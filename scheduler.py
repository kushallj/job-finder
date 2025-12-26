import schedule
import time
import asyncio
from main import main

def job():
    """Run the job automation"""
    asyncio.run(main())

# Run every 6 hours
schedule.every(6).hours.do(job)

print("⏰ Scheduler started. Running every 6 hours...")
while True:
    schedule.run_pending()
    time.sleep(60)