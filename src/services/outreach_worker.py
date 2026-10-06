"""
outreach_worker.py — Standalone Email Outreach & Discovery Engine Worker.
Monitors pending outreach cadences, validates corporate MX records, and executes rate-limited sends.
"""
import asyncio
import logging
import os
from src.database import SessionLocal, init_db
from src.outreach_processor import OutreachProcessor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("outreach_worker")


async def main():
    init_db()
    interval_sec = int(os.getenv("OUTREACH_INTERVAL_SECONDS", "300"))
    logger.info(f"📧 Email Outreach Engine Worker Container started (Interval: {interval_sec}s).")
    processor = OutreachProcessor()

    while True:
        try:
            logger.info("📬 Processing pending outreach queue and cadence follow-ups...")
            resume_path = os.getenv("RESUME_PATH", "data/resume.txt")
            resume_text = ""
            if os.path.exists(resume_path):
                with open(resume_path, "r", encoding="utf-8") as f:
                    resume_text = f.read()

            stats = await processor.process_multiple_jobs(
                resume_text=resume_text,
                max_contacts_per_job=int(os.getenv("MAX_CONTACTS_PER_JOB", "2")),
                send_emails=os.getenv("SEND_EMAILS", "true").lower() == "true"
            )
            logger.info(f"✅ Outreach cycle complete: {stats}. Standing by for {interval_sec}s...")
            await asyncio.sleep(interval_sec)
        except asyncio.CancelledError:
            logger.info("🛑 Outreach worker cancelled, shutting down gracefully...")
            break
        except Exception as err:
            logger.error(f"❌ Outreach worker recoverable exception: {err}", exc_info=True)
            await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
