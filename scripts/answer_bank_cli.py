#!/usr/bin/env python3
"""
answer_bank_cli.py — CLI for reviewing and managing the answer bank.

Mirrors outreach_cli.py's argparse style. Run standalone, or copy the
subparser blocks into outreach_cli.py's main() to fold these commands
into the existing `python outreach_cli.py ...` entrypoint.

Commands:
    python answer_bank_cli.py list-unapproved
    python answer_bank_cli.py approve --id 12
    python answer_bank_cli.py approve --id 12 --edit "New answer text"
    python answer_bank_cli.py add --question "..." --answer "..." --category visa_sponsorship
    python answer_bank_cli.py search --question "Do you need visa sponsorship?"
"""

import argparse

from src.database import SessionLocal
from src.answer_bank.service import AnswerBankService


def list_unapproved(limit=20):
    db = SessionLocal()
    bank = AnswerBankService(db)
    entries = bank.list_unapproved(limit=limit)

    if not entries:
        print("✅ No unapproved answers pending review.")
        db.close()
        return

    print(f"\n📋 {len(entries)} unapproved answer(s):\n")
    for e in entries:
        print(f"  [{e.id}] Q: {e.question_text}")
        print(f"       A: {e.answer_text}")
        print(f"       category={e.category or '-'}  context={e.context}\n")
    db.close()


def approve(answer_id: int, edited_text: str = None):
    db = SessionLocal()
    bank = AnswerBankService(db)
    entry = bank.approve(answer_id, edited_answer_text=edited_text)
    print(f"✅ Approved answer [{entry.id}]: {entry.answer_text}")
    db.close()


def add(question: str, answer: str, category: str = None, context: str = "ats_application"):
    db = SessionLocal()
    bank = AnswerBankService(db)
    entry = bank.save_answer(
        question_text=question,
        answer_text=answer,
        source="user_provided",
        category=category,
        context=context,
        approved=True,
    )
    print(f"✅ Saved answer [{entry.id}] for: {question}")
    db.close()


def search(question: str):
    db = SessionLocal()
    bank = AnswerBankService(db)
    hit = bank.find_cached_answer(question)
    if hit:
        print(f"✅ Match found (confidence={hit.match_confidence:.2f}, used {hit.times_used}x):")
        print(f"   Q: {hit.question_text}")
        print(f"   A: {hit.answer_text}")
        print(f"   approved={hit.approved}")
    else:
        print("❌ No cached answer found for this question.")
    db.close()


def main():
    parser = argparse.ArgumentParser(description="Answer Bank CLI Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    list_parser = subparsers.add_parser("list-unapproved", help="List AI-generated answers pending review")
    list_parser.add_argument("--limit", type=int, default=20)

    approve_parser = subparsers.add_parser("approve", help="Approve (optionally edit) an answer")
    approve_parser.add_argument("--id", type=int, required=True)
    approve_parser.add_argument("--edit", help="Replace the answer text before approving")

    add_parser = subparsers.add_parser("add", help="Manually add a pre-approved answer")
    add_parser.add_argument("--question", required=True)
    add_parser.add_argument("--answer", required=True)
    add_parser.add_argument("--category")
    add_parser.add_argument("--context", default="ats_application")

    search_parser = subparsers.add_parser("search", help="Check if a question has a cached answer")
    search_parser.add_argument("--question", required=True)

    args = parser.parse_args()

    if args.command == "list-unapproved":
        list_unapproved(args.limit)
    elif args.command == "approve":
        approve(args.id, args.edit)
    elif args.command == "add":
        add(args.question, args.answer, args.category, args.context)
    elif args.command == "search":
        search(args.question)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
