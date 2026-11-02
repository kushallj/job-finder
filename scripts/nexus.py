#!/usr/bin/env python3
"""
nexus.py — NEXUS DAG pipeline CLI entry point.

Replaces the linear comprehensive_job_search.py with a proper DAG-based
orchestration that:
  - Runs independent branches in parallel (tailor_resume + contact_intel)
  - Routes conditionally (skip feedback on dry runs)
  - Records timings and errors per node
  - Prints a clean summary at the end

Usage:
    python nexus.py                         # full run (sends emails)
    python nexus.py --dry-run               # no emails sent
    python nexus.py --queries "SWE" "MLE"  # custom search queries
    python nexus.py --max-jobs 3            # cap jobs per query
    python nexus.py --visualize             # print DAG topology and exit
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from src.database import init_db
from src.dag.state import NEXUSState
from src.dag.nexus_graph import build_nexus_graph, DEFAULT_CONFIG

logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s %(levelname)-7s %(name)s — %(message)s",
    datefmt = "%H:%M:%S",
)
log = logging.getLogger("nexus")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="NEXUS — Neural Execution for eXpert Unified Search"
    )
    p.add_argument(
        "--queries", "-q",
        nargs="+",
        default=DEFAULT_CONFIG["search_queries"],
        help="Search queries (space-separated)",
    )
    p.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Run full pipeline but skip sending emails",
    )
    p.add_argument(
        "--max-jobs",
        type=int,
        default=DEFAULT_CONFIG["max_jobs_per_query"],
        help="Max jobs per query to process",
    )
    p.add_argument(
        "--max-tailor",
        type=int,
        default=DEFAULT_CONFIG["max_jobs_to_tailor"],
        help="Max resume variants to generate",
    )
    p.add_argument(
        "--max-companies",
        type=int,
        default=DEFAULT_CONFIG["max_companies"],
        help="Max companies to run contact intelligence on",
    )
    p.add_argument(
        "--resume",
        default=DEFAULT_CONFIG["resume_path"],
        help="Path to base resume.txt",
    )
    p.add_argument(
        "--visualize", "-v",
        action="store_true",
        help="Print DAG topology and exit without running",
    )
    return p.parse_args()


async def run(args: argparse.Namespace) -> NEXUSState:
    # ── Validate ──────────────────────────────────────────────────────────────
    if not Path(args.resume).exists():
        log.error("Resume not found: %s", args.resume)
        sys.exit(1)

    # ── Init DB ───────────────────────────────────────────────────────────────
    init_db()

    # ── Build graph ───────────────────────────────────────────────────────────
    compiled = build_nexus_graph()

    if args.visualize:
        print(compiled.visualize())
        return None

    # ── Build initial state ───────────────────────────────────────────────────
    state = NEXUSState(
        search_queries     = args.queries,
        resume_path        = args.resume,
        dry_run            = args.dry_run,
        max_jobs_per_query = args.max_jobs,
        max_jobs_to_tailor = args.max_tailor,
        max_companies      = args.max_companies,
    )

    # ── Run DAG ───────────────────────────────────────────────────────────────
    mode = "DRY RUN" if args.dry_run else "LIVE"
    log.info("NEXUS [%s] starting — %d queries", mode, len(state.search_queries))

    result = await compiled.run(state)

    # ── Print summary ─────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(result.summary())
    print("=" * 60 + "\n")

    if result.feedback_snapshot:
        print(result.feedback_snapshot.digest_markdown[:2000])

    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for e in result.errors:
            print(f"  • {e}")

    return result


def main() -> None:
    args   = parse_args()
    result = asyncio.run(run(args))
    if result and result.errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
