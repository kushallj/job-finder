"""python -m src.job_sources --list | "<query>" [--location X] [--limit N] [--store]"""

from __future__ import annotations

import argparse
import asyncio

from src.job_sources import SearchQuery, describe, fetch_and_store, fetch_jobs


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m src.job_sources", description="Fetch jobs from every enabled source.")
    ap.add_argument("query", nargs="?", help="search text, e.g. 'python developer'")
    ap.add_argument("--location", default="")
    ap.add_argument("--limit", type=int, default=50, help="max results per source")
    ap.add_argument("--store", action="store_true", help="insert new jobs into DATABASE_URL")
    ap.add_argument("--list", action="store_true", help="show every source and whether it would run")
    args = ap.parse_args()

    if args.list or not args.query:
        for s in describe():
            mark = "ON " if s["active"] else ("key" if not s["configured"] else "off")
            print(f"[{mark}] {s['name']:<15} {s['tier']:<13} {s['description']}")
        return

    q = SearchQuery(args.query, location=args.location, limit=args.limit)
    if args.store:
        from src.database import SessionLocal

        with SessionLocal() as db:
            stored, report = asyncio.run(fetch_and_store(db, q))
        print(f"stored {stored} new jobs")
    else:
        report = asyncio.run(fetch_jobs(q))
    for s in report.sources:
        print(f"  {s.name:<15} {s.status:<8} {s.count:>4} jobs  {s.seconds:>5.1f}s  {s.error or ''}")
    print(report.summary())


if __name__ == "__main__":
    main()
