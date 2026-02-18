#!/usr/bin/env python3
"""
Comprehensive Job Search and Outreach System

This script searches across multiple platforms and automatically initiates outreach campaigns.
"""

import asyncio
import os
from src.job_processor import JobProcessor
from src.outreach_processor import OutreachProcessor
from src.scrapers.multi_platform_scraper import MultiPlatformJobScraper
from src.database import init_db

async def main():
    """Comprehensive job search and outreach workflow"""
    print("🚀 Comprehensive Job Search & Outreach System Starting...")
    print("=" * 60)

    # Initialize database
    init_db()

    # Create processors
    job_processor = JobProcessor()
    outreach_processor = OutreachProcessor()
    multi_platform_scraper = MultiPlatformJobScraper()

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

        # Step 1: Comprehensive Multi-Platform Job Search
        print("\n🔍 Step 1: Comprehensive Multi-Platform Job Search")
        print("-" * 50)
        
        # Search using enhanced API scraper (includes multi-platform)
        enhanced_queries = [
            "Python Developer",
            "Backend Developer", 
            "Full Stack Developer",
            "Software Engineer",
            "Django Developer",
            "FastAPI Developer",
            "GenAI Engineer",
            "Machine Learning Engineer"
        ]
        
        total_new_jobs = 0
        for query in enhanced_queries:
            print(f"\n🎯 Searching for: {query}")
            new_jobs = await job_processor.fetch_and_store_jobs(query=query)
            total_new_jobs += new_jobs
            
            # Brief pause between queries
            await asyncio.sleep(3)

        print(f"\n✅ Total new jobs found across all platforms: {total_new_jobs}")

        # Step 2: AI-Powered Job Analysis
        print("\n🤖 Step 2: AI-Powered Job Analysis & Matching")
        print("-" * 50)
        
        # Process jobs with higher threshold for outreach
        await job_processor.process_all_jobs(resume_text, min_score=65)

        # Step 3: Multi-Platform Search Report
        print("\n📊 Step 3: Multi-Platform Search Report")
        print("-" * 50)
        
        # Generate comprehensive report
        report = multi_platform_scraper.generate_report()
        if report:
            print(f"📈 Search Summary:")
            print(f"   Total Jobs Analyzed: {report.get('total_jobs', 0)}")
            print(f"   Remote Jobs: {report.get('remote_jobs', 0)}")
            
            print(f"\n📍 Top Job Sources:")
            for source, count in list(report.get('by_source', {}).items())[:5]:
                print(f"   {source}: {count} jobs")
            
            print(f"\n🏢 Top Companies:")
            for company, count in list(report.get('by_company', {}).items())[:8]:
                print(f"   {company}: {count} jobs")
            
            print(f"\n📍 Top Locations:")
            for location, count in list(report.get('by_location', {}).items())[:5]:
                print(f"   {location}: {count} jobs")

        # Step 4: Intelligent Outreach Campaign
        print("\n📧 Step 4: Intelligent Outreach Campaign")
        print("-" * 50)
        
        # Check if resume PDF exists
        resume_pdf_path = "data/resume.pdf"
        if not os.path.exists(resume_pdf_path):
            print("⚠️  Resume PDF not found. Creating from text resume...")
            try:
                import subprocess
                result = subprocess.run(["python", "create_resume_pdf.py"], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    print("✅ Resume PDF created successfully")
                else:
                    print("❌ Failed to create resume PDF. Please run: python create_resume_pdf.py")
                    return
            except Exception as e:
                print(f"❌ Error creating resume PDF: {e}")
                return

        # Run outreach campaign
        outreach_stats = await outreach_processor.process_multiple_jobs(
            resume_text=resume_text,
            max_contacts_per_job=2,  # Contact 2 people per company
            send_emails=True  # Set to False for dry run
        )

        # Step 5: Campaign Results & Next Steps
        print("\n🎉 Step 5: Campaign Results & Recommendations")
        print("-" * 50)
        
        print(f"📊 Outreach Campaign Results:")
        print(f"   Jobs Processed: {outreach_stats['jobs_processed']}")
        print(f"   Contacts Found: {outreach_stats['total_contacts_found']}")
        print(f"   Emails Sent: {outreach_stats['total_emails_sent']}")
        print(f"   Jobs with Contacts: {outreach_stats['jobs_with_contacts']}")

        # Overall statistics
        overall_stats = outreach_processor.get_outreach_stats()
        print(f"\n📈 Overall Campaign Statistics:")
        print(f"   Total Contacts in Database: {overall_stats['total_contacts']}")
        print(f"   Total Outreach Attempts: {overall_stats['total_outreach_attempts']}")
        print(f"   Companies Contacted: {overall_stats['companies_contacted']}")
        
        if overall_stats.get('top_companies'):
            print(f"\n🏢 Top Companies Contacted:")
            for company, count in overall_stats['top_companies'][:5]:
                print(f"   {company}: {count} contacts")

        # Success metrics and recommendations
        if outreach_stats['total_emails_sent'] > 0:
            success_rate = (outreach_stats['jobs_with_contacts'] / outreach_stats['jobs_processed']) * 100
            print(f"\n📈 Success Metrics:")
            print(f"   Contact Discovery Rate: {success_rate:.1f}%")
            print(f"   Average Contacts per Job: {outreach_stats['total_contacts_found'] / max(outreach_stats['jobs_processed'], 1):.1f}")

        print(f"\n💡 Next Steps & Recommendations:")
        print(f"   1. 📧 Monitor your email (canaby007@gmail.com) for replies")
        print(f"   2. 📅 Set calendar reminders to follow up in 1 week")
        print(f"   3. 📊 Track response rates and adjust approach")
        print(f"   4. 🔄 Run this script weekly for new opportunities")
        print(f"   5. 🎯 Focus on companies that showed interest")

        # Platform-specific insights
        print(f"\n🔍 Platform Insights:")
        print(f"   • Naukri & Indeed: High volume, good for junior-mid level")
        print(f"   • Hirist: Tech-focused, quality over quantity")
        print(f"   • Remote.co: Remote opportunities, global companies")
        print(f"   • Foorilla: Job aggregation platform with diverse listings")
        print(f"   • Company Career Pages: Direct applications, higher success rate")

        print(f"\n✅ Comprehensive job search and outreach campaign completed!")
        print(f"🎯 You're now actively in the pipeline of {outreach_stats['total_emails_sent']} potential opportunities!")

    except Exception as e:
        print(f"❌ Error in comprehensive job search: {e}")
        raise
    finally:
        job_processor.close()
        await job_processor.scraper.close()
        await outreach_processor.close()

if __name__ == "__main__":
    asyncio.run(main())