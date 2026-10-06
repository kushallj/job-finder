"""
worker.py — Standalone Autonomous Crawler & Scrapers Worker Process.
Executes continuous sweeps across 60 Tier-1 Tech Giants, 109 Indian App Startups,
140 FinTech Festival companies, and external job aggregators.
"""
import asyncio
import logging
import os
from src.autonomous_job_crawler import autonomous_crawler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("crawler_worker")


async def main():
    interval_sec = int(os.getenv("CRAWLER_INTERVAL_SECONDS", "180"))
    logger.info(f"🚀 Autonomous Crawler Worker Container initialized (Interval: {interval_sec}s).")
    
    while True:
        try:
            logger.info("🔄 Initiating autonomous sweep across Tier-1, Startups, and Aggregators...")
            stats = await autonomous_crawler.run_single_pass()
            logger.info(f"✅ Sweep completed: {stats}. Sleeping {interval_sec}s...")
            await asyncio.sleep(interval_sec)
        except asyncio.CancelledError:
            logger.info("🛑 Crawler worker cancelled, shutting down gracefully...")
            break
        except Exception as err:
            logger.error(f"❌ Crawler worker recoverable error: {err}", exc_info=True)
            await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(main())
