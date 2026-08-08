#!/bin/bash
# start.sh — launch the full NEXUS stack
# Usage: ./start.sh [--no-flower]
#
# Starts:
#   - FastAPI server      (port 8000)
#   - Celery worker       (4 concurrent slots)
#   - Celery beat         (scheduler, replaces crontab)
#   - Flower monitor      (port 5555, skip with --no-flower)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$ROOT/.venv/bin/python"
CELERY="$ROOT/.venv/bin/celery"
UVICORN="$ROOT/.venv/bin/uvicorn"
LOG_DIR="$ROOT/logs"

mkdir -p "$LOG_DIR"

NO_FLOWER=false
for arg in "$@"; do [[ "$arg" == "--no-flower" ]] && NO_FLOWER=true; done

cd "$ROOT"

# ── Load .env (handles spaces around = and trailing whitespace) ───────────────
while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*=[[:space:]]*(.*) ]]; then
        key="${BASH_REMATCH[1]}"
        val="${BASH_REMATCH[2]%"${BASH_REMATCH[2]##*[![:space:]]}"}"
        export "$key"="$val"
    fi
done < "$ROOT/.env"

# ── Cleanup on exit ───────────────────────────────────────────────────────────
PIDS=()
cleanup() {
    echo ""
    echo "⏹  Stopping NEXUS…"
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null
    echo "✅ All processes stopped."
}
trap cleanup EXIT INT TERM

# ── Start processes ───────────────────────────────────────────────────────────
echo "🚀 Starting NEXUS stack…"

"$UVICORN" main:app --host 0.0.0.0 --port 8000 --log-level info \
    >> "$LOG_DIR/server.log" 2>&1 &
PIDS+=($!)
echo "  ✅ API server    PID=$! → logs/server.log"

"$CELERY" -A src.tasks worker \
    --loglevel=info --concurrency=4 \
    >> "$LOG_DIR/worker.log" 2>&1 &
PIDS+=($!)
echo "  ✅ Celery worker PID=$! → logs/worker.log"

"$CELERY" -A src.tasks beat \
    --loglevel=info \
    --scheduler celery.beat.PersistentScheduler \
    >> "$LOG_DIR/beat.log" 2>&1 &
PIDS+=($!)
echo "  ✅ Celery beat   PID=$! → logs/beat.log"

if [[ "$NO_FLOWER" == false ]]; then
    "$CELERY" -A src.tasks flower --port=5555 \
        >> "$LOG_DIR/flower.log" 2>&1 &
    PIDS+=($!)
    echo "  ✅ Flower UI     PID=$! → http://localhost:5555"
fi

echo ""
echo "  API:    http://localhost:8000"
echo "  ngrok:  check \`curl http://localhost:4040/api/tunnels\`"
echo "  Flower: http://localhost:5555"
echo ""
echo "  Logs:   tail -f logs/worker.log logs/beat.log"
echo ""
echo "Press Ctrl+C to stop all processes."

wait
