#!/usr/bin/env python3
"""
scripts/fetch_sp500_referrals.py — Standalone runner to mine LinkedIn & X referral contacts
for all S&P 500 tech companies with live roles in SQLite.
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.scrapers.sp500_referral_miner import SP500ReferralMiner

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("fetch_sp500_referrals")


async def main():
    logger.info("⚡ Initializing S&P 500 LinkedIn & X Referral Mining Engine...")
    miner = SP500ReferralMiner()
    stats = await miner.mine_and_sync_all_sp500_referrals(auto_send=False)
    logger.info("🎯 S&P 500 Referral Mining Complete:")
    logger.info(f" - Companies Processed: {stats['companies_processed']}")
    logger.info(f" - LinkedIn Referrals: {stats['linkedin_contacts']}")
    logger.info(f" - X (Twitter) Referrals: {stats['x_contacts']}")
    logger.info(f" - Total Contacts Ingested: {stats['total_saved']}")


if __name__ == "__main__":
    asyncio.run(main())
