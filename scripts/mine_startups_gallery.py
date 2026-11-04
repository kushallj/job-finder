#!/usr/bin/env python3
"""
scripts/mine_startups_gallery.py — Repeatable Batch Mining CLI for startups.gallery

Usage:
  # Check status across all 1,369 startups
  python3 scripts/mine_startups_gallery.py --status

  # Mine the next 100 unmined companies and export to JSON & CSV
  python3 scripts/mine_startups_gallery.py --batch-size 100 --export-json data/founders.json --export-csv data/founders.csv

  # Mine 50 companies specifically in AI
  python3 scripts/mine_startups_gallery.py --batch-size 50 --category AI

  # Reset all mined statuses to start fresh
  python3 scripts/mine_startups_gallery.py --reset
"""
import argparse
import asyncio
import csv
import json
import os
import sys

# Ensure repository root is on Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import SessionLocal, init_db
from src.models import Contact, StartupsGalleryCompanyRecord
from src.startups_gallery_miner import startups_gallery_miner


def print_status():
    """Print current mining metrics across all 1,369 companies."""
    init_db()
    status = startups_gallery_miner.get_status()
    print("=" * 60)
    print("🚀 startups.gallery Mining Progress")
    print("=" * 60)
    print(f"Total Companies in Registry : {status['total_companies']}")
    print(f"Mined Companies             : {status['mined_companies']} ({status['completion_percentage']}%)")
    print(f"Pending Companies           : {status['pending_companies']}")
    print("-" * 60)
    print(f"Total Founders Extracted    : {status['total_founders_mined']}")
    print(f"Founders with LinkedIn      : {status['founders_with_linkedin']}")
    print(f"Founders with X (Twitter)   : {status['founders_with_twitter']}")
    print(f"Founders with Business Email: {status['founders_with_email']}")
    print("=" * 60)


def export_data(contacts, json_path=None, csv_path=None):
    """Export contacts list to JSON and/or CSV files with investors and open jobs data."""
    if not contacts:
        print("ℹ️ No contacts to export.")
        return

    if json_path:
        os.makedirs(os.path.dirname(os.path.abspath(json_path)), exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(contacts, f, indent=2)
        print(f"✅ Exported {len(contacts)} contacts to JSON: {json_path}")

    if csv_path:
        os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)
        keys = [
            "name",
            "title",
            "company",
            "category",
            "location",
            "funding",
            "investors",
            "jobs_count",
            "open_jobs",
            "ats_url",
            "email",
            "linkedin_url",
            "twitter_url",
        ]
        rows = []
        for c in contacts:
            inv = c.get("investors")
            inv_str = ", ".join(inv) if isinstance(inv, list) else (c.get("investors_str") or str(inv or ""))
            jobs = c.get("open_jobs") or c.get("jobs")
            jobs_str = " | ".join(jobs) if isinstance(jobs, list) else (c.get("open_jobs_str") or str(jobs or ""))
            rows.append({
                "name": c.get("name", ""),
                "title": c.get("title", ""),
                "company": c.get("company", ""),
                "category": c.get("category", ""),
                "location": c.get("location", ""),
                "funding": c.get("funding", ""),
                "investors": inv_str,
                "jobs_count": c.get("jobs_count", 0),
                "open_jobs": jobs_str,
                "ats_url": c.get("ats_url", ""),
                "email": c.get("email", ""),
                "linkedin_url": c.get("linkedin_url", ""),
                "twitter_url": c.get("twitter_url", ""),
            })

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        print(f"✅ Exported {len(rows)} contacts to CSV: {csv_path}")


def reset_mined_state():
    """Reset mined state for all companies."""
    init_db()
    with SessionLocal() as db:
        updated = db.query(StartupsGalleryCompanyRecord).update({
            StartupsGalleryCompanyRecord.mined: False,
            StartupsGalleryCompanyRecord.mined_at: None,
            StartupsGalleryCompanyRecord.founders_count: 0,
        })
        db.commit()
    print(f"🔄 Reset {updated} companies to unmined state.")


async def main():
    parser = argparse.ArgumentParser(description="Repeatable batch miner for startups.gallery founders.")
    parser.add_argument("--batch-size", type=int, default=100, help="Number of unmined companies to scrape (default: 100)")
    parser.add_argument("--category", type=str, default=None, help="Filter by sector (e.g. AI, Fintech, DevTools)")
    parser.add_argument("--offset", type=int, default=None, help="Manual offset override in company list")
    parser.add_argument("--export-json", type=str, default=None, help="Destination JSON path")
    parser.add_argument("--export-csv", type=str, default=None, help="Destination CSV path")
    parser.add_argument("--status", action="store_true", help="Display mining stats and exit")
    parser.add_argument("--reset", action="store_true", help="Reset all companies to unmined")
    parser.add_argument("--auto-send", action="store_true", help="Send cold outreach emails within daily quota")
    parser.add_argument("--no-twitter", action="store_true", help="Skip X (Twitter) search queries")

    args = parser.parse_args()

    init_db()

    if args.status:
        print_status()
        return

    if args.reset:
        reset_mined_state()
        print_status()
        return

    print(f"⚡ Starting batch mine: {args.batch_size} companies" + (f" in category '{args.category}'" if args.category else ""))
    
    result = await startups_gallery_miner.batch_mine(
        batch_size=args.batch_size,
        category=args.category,
        offset=args.offset,
        auto_send=args.auto_send,
        extract_twitter=not args.no_twitter,
    )

    print("\n" + "=" * 60)
    print(result.get("message", "Mining complete."))
    print("=" * 60)

    contacts = result.get("contacts", [])
    if contacts:
        export_data(contacts, json_path=args.export_json, csv_path=args.export_csv)
    else:
        # If no new contacts mined in this batch, optionally export all previously mined contacts
        if args.export_json or args.export_csv:
            with SessionLocal() as db:
                all_records = db.query(Contact).filter(Contact.source == "startups_gallery").all()
                all_data = [
                    {
                        "name": c.name,
                        "title": c.title,
                        "company": c.company,
                        "email": c.email,
                        "linkedin_url": c.linkedin_url,
                        "twitter_url": c.twitter_url,
                        "category": c.department,
                    }
                    for c in all_records
                ]
            export_data(all_data, json_path=args.export_json, csv_path=args.export_csv)

    print("\n📊 Updated Status:")
    print_status()


if __name__ == "__main__":
    asyncio.run(main())
