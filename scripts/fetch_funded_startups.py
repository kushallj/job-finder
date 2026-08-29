import sys
import os
import asyncio
import logging
import argparse
import time
from typing import List, Tuple, Set

# Add project root to sys.path to allow running from anywhere within the project
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.news_service import NewsService, FirecrawlNewsService
from src.scrapers.firecrawl_scraper import TOP_INDIAN_STARTUPS

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger("fetch_startups")

async def main(target_count: int = 1000, use_firecrawl: bool = True, duration_hours: float = 0):
    start_time = time.time()
    end_time = start_time + (duration_hours * 3600) if duration_hours > 0 else start_time
    
    log.info(f"Gathering recently funded Indian startups (target: {target_count}, provider: {'Firecrawl' if use_firecrawl else 'NewsAPI'})...")
    if duration_hours > 0:
        log.info(f"Running for {duration_hours} hours...")

    # Tracking found companies to avoid duplicates across iterations
    found_companies: Set[str] = {name.lower() for name, _ in TOP_INDIAN_STARTUPS}
    all_to_add: List[Tuple[str, str]] = []

    iteration = 0
    while True:
        iteration += 1
        if duration_hours > 0:
            log.info(f"Iteration {iteration}...")

        if use_firecrawl:
            service = FirecrawlNewsService()
            # We can vary queries slightly or just rely on new news items
            new_startup_names = await service.fetch_funded_startups(limit=target_count)
        else:
            service = NewsService()
            # Fetch funded startups using news API
            new_startup_names = await service.fetch_funded_startups(pages=10)
        
        if new_startup_names:
            log.info(f"Found {len(new_startup_names)} potential startups via news in this iteration.")
            
            newly_added_in_iter = 0
            for name in new_startup_names:
                if name.lower() not in found_companies:
                    found_companies.add(name.lower())
                    # Best guess: https://www.{name}.com/careers
                    guess_url = f"https://www.{name.lower().replace(' ', '')}.com/careers"
                    all_to_add.append((name, guess_url))
                    newly_added_in_iter += 1
                    
                    # Print immediately so user can see progress
                    print(f'    ("{name}", "{guess_url}"),')

                    if len(all_to_add) >= target_count:
                        log.info(f"Reached target count of {target_count} startups.")
                        await service.close()
                        return

            log.info(f"Added {newly_added_in_iter} new unique startups in this iteration. Total unique added: {len(all_to_add)}")
        else:
            log.warning(f"No new startups found via {'Firecrawl' if use_firecrawl else 'News API'} in this iteration.")

        await service.close()

        # Check if duration is met
        if duration_hours > 0:
            remaining = end_time - time.time()
            if remaining <= 0:
                log.info("Requested duration completed.")
                break
            
            # Sleep between iterations to avoid hitting rate limits and wait for new news
            sleep_time = min(300, remaining) # Sleep for 5 mins or until end
            log.info(f"Sleeping for {sleep_time} seconds before next iteration...")
            await asyncio.sleep(sleep_time)
        else:
            # If no duration, just run once
            break

    log.info(f"Finished. Total unique startups added to list: {len(all_to_add)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--provider", choices=["firecrawl", "newsapi"], default="firecrawl")
    parser.add_argument("--duration", type=float, default=0, help="Duration to run in hours (e.g., 2.0)")
    args = parser.parse_args()
    asyncio.run(main(args.count, use_firecrawl=(args.provider == "firecrawl"), duration_hours=args.duration))
