import asyncio
import os
from src.job_processor import JobProcessor
from src.outreach_processor import OutreachProcessor
from src.database import init_db

async def main():
    """Main entry point for job outreach automation"""
    print("🎯 Job Outreach Automation Starting...")

    # Initialize database
    init_db()

    # Create processors
    job_processor = JobProcessor()
    outreach_processor = OutreachProcessor()

    try:
        # Load resume
        resume_path = "data/resume.txt"
        if not os.path.exists(resume_path):
            print("❌ Resume file not found at data/resume.txt")
            print("Please create a resume file with your background and experience.")
            return

        with open(resume_path, "r") as f:
            resume_text = f.read()

        print("📄 Resume loaded successfully")

        # Step 1: Fetch fresh jobs (optional - you can skip this if you have jobs already)
        print("\n🔍 Step 1: Fetching fresh job opportunities...")
        queries = ["python developer", "software engineer", "backend developer"]
        
        for query in queries:
            await job_processor.fetch_and_store_jobs(query=query)
            await asyncio.sleep(5)  # Brief pause between queries

        # Step 2: Find high-match jobs for outreach
        print("\n🤖 Step 2: Analyzing job matches...")
        await job_processor.process_all_jobs(resume_text, min_score=60)  # Higher threshold for outreach

        # Step 3: Process outreach for top jobs
        print("\n📧 Step 3: Starting outreach campaign...")
        
        # You can either:
        # A) Process all jobs needing outreach
        outreach_stats = await outreach_processor.process_multiple_jobs(
            resume_text=resume_text,
            max_contacts_per_job=2,  # Contact 2 people per company
            send_emails=True  # Set to False for dry run
        )
        
        # B) Or target specific job IDs
        # specific_job_ids = [1, 2, 3]  # Replace with actual job IDs
        # outreach_stats = await outreach_processor.process_multiple_jobs(
        #     job_ids=specific_job_ids,
        #     resume_text=resume_text,
        #     max_contacts_per_job=2,
        #     send_emails=True
        # )

        # Step 4: Show results
        print("\n📊 Outreach Campaign Results:")
        print(f"   Jobs processed: {outreach_stats['jobs_processed']}")
        print(f"   Contacts found: {outreach_stats['total_contacts_found']}")
        print(f"   Emails sent: {outreach_stats['total_emails_sent']}")
        print(f"   Jobs with contacts: {outreach_stats['jobs_with_contacts']}")

        # Show overall stats
        print("\n📈 Overall Outreach Statistics:")
        overall_stats = outreach_processor.get_outreach_stats()
        print(f"   Total contacts in database: {overall_stats['total_contacts']}")
        print(f"   Total outreach attempts: {overall_stats['total_outreach_attempts']}")
        print(f"   Companies contacted: {overall_stats['companies_contacted']}")
        
        if overall_stats['top_companies']:
            print("   Top companies contacted:")
            for company, count in overall_stats['top_companies'][:5]:
                print(f"     - {company}: {count} contacts")

        print("\n✅ Outreach campaign completed!")
        print("\n💡 Next steps:")
        print("   1. Monitor your email for replies")
        print("   2. Follow up with non-responders after 1 week")
        print("   3. Track responses and update contact status")
        print("   4. Run the campaign again for new jobs")

    except Exception as e:
        print(f"❌ Error in outreach campaign: {e}")
        raise
    finally:
        job_processor.close()
        await job_processor.scraper.close()
        await outreach_processor.close()

if __name__ == "__main__":
    asyncio.run(main())