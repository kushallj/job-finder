#!/bin/bash
# nexus_cron.sh — NEXUS full pipeline cron runner (100% local, no Claude agents)
#
# Every 2 hours:
#   1. Scrape new jobs from all sources
#   2. Keyword-score all new jobs instantly (seconds)
#   3. Run top 15 new matches through full NEXUS DAG:
#      qwen2.5:3b LLM → contact intel → personalized outreach drafts
#   4. Regenerate data/applications.md tracker
#
# Requires: Ollama running with qwen2.5:3b pulled
# Logs:     logs/nexus_cron.log

set -euo pipefail

PROJECT="/Users/kushalljain/Desktop/job-finder"
PYTHON="$PROJECT/.venv/bin/python"
LOG="$PROJECT/logs/nexus_cron.log"
STAMP=$(date '+%Y-%m-%d %H:%M:%S')

cd "$PROJECT"

# ── Load .env safely (handles spaces around = and trailing whitespace) ─────────
while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*=[[:space:]]*(.*) ]]; then
        key="${BASH_REMATCH[1]}"
        val="${BASH_REMATCH[2]%"${BASH_REMATCH[2]##*[![:space:]]}"}"
        export "$key"="$val"
    fi
done < "$PROJECT/.env"

echo ""                                              >> "$LOG"
echo "=========================================="   >> "$LOG"
echo "NEXUS cron run started: $STAMP"               >> "$LOG"
echo "=========================================="   >> "$LOG"

# ── 1. Scrape new jobs ─────────────────────────────────────────────────────────
echo "[1/4] Scraping new jobs..."                   >> "$LOG"
"$PYTHON" -c "
import asyncio, sys
sys.path.insert(0, '.')
from src.job_processor import JobProcessor, ProcessorConfig

QUERIES = [
    'Senior Python Engineer',
    'Backend Developer FastAPI',
    'Full Stack Developer React Python',
    'Software Development Engineer',
    'Django Developer',
]

async def run():
    cfg = ProcessorConfig(auto_send_emails=False)
    p   = JobProcessor(config=cfg)
    total = 0
    for q in QUERIES:
        try:
            n = await p.fetch_and_store_jobs(query=q)
            total += (n or 0)
        except Exception as e:
            print(f'  scrape failed [{q}]: {e}', file=sys.stderr)
    await p.close()
    print(f'  stored {total} new jobs')

asyncio.run(run())
" >> "$LOG" 2>&1

# ── 2. Keyword-score ALL new unprocessed jobs (instant) ────────────────────────
echo "[2/4] Keyword-scoring all new unprocessed jobs..." >> "$LOG"
TOP_IDS_FILE=$(mktemp /tmp/nexus_top_ids.XXXXXX)

"$PYTHON" -c "
import asyncio, json, sys
from datetime import datetime
from sqlalchemy.exc import IntegrityError
sys.path.insert(0, '.')
from src.database import SessionLocal, init_db
from src.models import Job, Application
from src.ai.fallback_service import FallbackAIService

init_db()

async def run():
    db  = SessionLocal()
    ai  = FallbackAIService()
    unprocessed = (
        db.query(Job)
        .outerjoin(Application, Application.job_id == Job.id)
        .filter(Application.id == None)
        .order_by(Job.id.desc())
        .all()
    )
    if not unprocessed:
        open('$TOP_IDS_FILE', 'w').write('[]')
        print('  no new jobs to score')
        db.close()
        return

    resume  = open('data/resume.txt').read()
    scored  = []

    for job in unprocessed:
        skills = await ai.extract_skills(job.description or '')
        match  = await ai.match_resume_to_job(resume, skills)
        score  = match['match_score']
        try:
            app = Application(
                job_id         = job.id,
                match_score    = score,
                skills_matched = json.dumps(match['matched_skills']),
                skills_missing = json.dumps(match['missing_skills']),
                status         = 'ready',
                created_at     = datetime.utcnow(),
                updated_at     = datetime.utcnow(),
            )
            db.add(app)
            db.commit()
            scored.append((job.id, score))
        except IntegrityError:
            db.rollback()

    db.close()
    top = sorted(scored, key=lambda x: x[1], reverse=True)[:15]
    top_ids = [jid for jid, _ in top]
    open('$TOP_IDS_FILE', 'w').write(json.dumps(top_ids))
    print(f'  scored {len(scored)} jobs — top {len(top_ids)} sent to LLM pass')

asyncio.run(run())
" >> "$LOG" 2>&1

NEW_JOB_IDS=$(cat "$TOP_IDS_FILE")
rm -f "$TOP_IDS_FILE"
echo "  top job IDs: $NEW_JOB_IDS" >> "$LOG"

# ── 3. Full NEXUS pipeline (LLM + contact intel + personalization) on top 15 ──
echo "[3/4] Running full NEXUS pipeline on top matches (local qwen2.5)..." >> "$LOG"
"$PYTHON" -c "
import asyncio, json, sys
sys.path.insert(0, '.')

top_ids = json.loads('$NEW_JOB_IDS')
if not top_ids:
    print('  no high-scoring new jobs — skipping LLM pass')
    sys.exit(0)

from src.database import SessionLocal, init_db
from src.models import Job
from src.dag.state import NEXUSState
from src.dag.nexus_graph import build_nexus_graph

init_db()

async def run():
    # Load the top-scoring jobs from DB
    db   = SessionLocal()
    jobs = db.query(Job).filter(Job.id.in_(top_ids)).all()
    db.close()

    if not jobs:
        print('  no jobs found in DB')
        return

    print(f'  running full pipeline on {len(jobs)} jobs...')

    graph = build_nexus_graph()
    state = NEXUSState(
        search_queries     = [],       # skip scraping — jobs already loaded
        resume_path        = 'data/resume.txt',
        dry_run            = True,     # draft outreach, don't send
        max_jobs_per_query = len(jobs),
        max_jobs_to_tailor = len(jobs),
        max_companies      = 10,
        company_size_hint  = 150,
    )

    # Inject the pre-loaded jobs directly so scrape_node is a no-op
    state.scraped_jobs = jobs

    result = await graph.run(state)

    print(f'  JDs analyzed:    {len(result.jd_analyses)}')
    print(f'  Resumes tailored:{len(result.resume_variants)} (avg ATS {result.avg_ats_score:.0f}/100)')
    print(f'  Contacts found:  {len(result.top_contacts)}')
    print(f'  Outreaches:      {len(result.personalized_outreaches)} (avg score {result.avg_personalization_score:.0f}/100)')
    print(f'  Runtime:         {sum(result.node_timings_ms.values())/1000:.1f}s')

    if result.errors:
        print(f'  Errors: {result.errors[:3]}')

asyncio.run(run())
" >> "$LOG" 2>&1

# ── 4. Regenerate tracker ──────────────────────────────────────────────────────
echo "[4/4] Regenerating tracker..."  >> "$LOG"
"$PYTHON" -m src.tracker              >> "$LOG" 2>&1

echo "NEXUS cron complete: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG"
