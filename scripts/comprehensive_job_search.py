#!/usr/bin/env python3
"""
Comprehensive Job Search and Outreach System

This script searches across multiple platforms and automatically initiates outreach campaigns.

Usage:
    python comprehensive_job_search.py                 # Default (sequential processing)
    python comprehensive_job_search.py --async-mode  # Using async_pipeline optimization
    python comprehensive_job_search.py -a             # Short flag for async
"""

import asyncio
import argparse
import os
import json
from src.job_processor import JobProcessor
from src.outreach_processor import OutreachProcessor
from src.scrapers.multi_platform_scraper import MultiPlatformJobScraper
from src.database import init_db

# Try to import async_pipeline
try:
    from src.async_pipeline import AsyncJobPipeline, ProcessorConfig
    _ASYNC_PIPELINE_OK = True
except Exception as e:
    _ASYNC_PIPELINE_OK = False
    print(f"Warning: async_pipeline not available: {e}")

async def main(use_async: bool = False):
    """Comprehensive job search and outreach workflow
    
    Args:
        use_async: If True, use AsyncJobPipeline for high-performance processing
    """
    print("🚀 Comprehensive Job Search & Outreach System Starting...")
    print("=" * 60)
    
    if use_async:
        print("⚡ Using AsyncJobPipeline for high-performance processing")
    else:
        print("🔄 Using standard sequential processing")

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
        
        if use_async and _ASYNC_PIPELINE_OK:
            # Use AsyncJobPipeline for high-performance processing
            print("⚡ Using AsyncJobPipeline for job processing...")
            
            # Create the async pipeline
            config = ProcessorConfig(
                worker_count=5,
                queue_size=100,
                max_concurrent_api_calls=3,
                llm_rate_limit=10,
                email_rate_limit=2,
                scraper_rate_limit=30,
                log_level="INFO",
            )
            async_pipeline = AsyncJobPipeline(config=config)
            
            # Import required modules for the processor
            from src.async_pipeline.types import JobContext, ProcessingResult
            from src.ai.unified_ai_service import UnifiedAIService
            from src.database import SessionLocal
            from src.models import Application, Job
            
            # Store resume_text in a scope accessible by the processor
            resume_text_for_processor = resume_text
            min_score_for_processor = 65
            
            async def process_job(job_ctx: JobContext) -> ProcessingResult:
                """Process a single job using AI services."""
                try:
                    session = SessionLocal()
                    try:
                        job = session.query(Job).filter(Job.id == job_ctx.job_id).first()
                        if not job:
                            return ProcessingResult.failure(
                                job_id=job_ctx.job_id,
                                error="Job not found"
                            )
                        
                        ai = UnifiedAIService()
                        job_skills = await ai.extract_skills(job.description or "")
                        match_result = await ai.match_resume_to_job(resume_text_for_processor, job_skills)
                        score = match_result["match_score"]
                        
                        if score < min_score_for_processor:
                            return ProcessingResult.success(
                                job_id=job_ctx.job_id,
                                data={"skipped": True, "score": score}
                            )
                        
                        rewritten_resume, cover_letter = await asyncio.gather(
                            ai.rewrite_resume(resume_text_for_processor, job.description or ""),
                            ai.generate_cover_letter(resume_text_for_processor, job.description or "", job.company or "")
                        )
                        
                        application = Application(
                            job_id=job.id,
                            match_score=score,
                            skills_matched=json.dumps(match_result["matched_skills"]),
                            skills_missing=json.dumps(match_result["missing_skills"]),
                            resume_version=rewritten_resume,
                            cover_letter=cover_letter,
                            status="ready",
                        )
                        session.add(application)
                        session.commit()
                        
                        return ProcessingResult.success(
                            job_id=job_ctx.job_id,
                            data={"score": score, "matched_skills": match_result["matched_skills"]}
                        )
                    finally:
                        session.close()
                except Exception as e:
                    return ProcessingResult.failure(job_id=job_ctx.job_id, error=str(e))
            
            # Set processor and run
            async_pipeline.set_processor(process_job)
            results = await async_pipeline.run(
                query="",
                resume_text=resume_text,
                filters={"min_score": 65}
            )
            
            stats = async_pipeline.stats
            print(f"✅ Async pipeline processed: {stats.jobs_completed} completed, {stats.jobs_failed} failed")
            
            await async_pipeline.close()
        else:
            # Use standard sequential processing
            print("🔄 Using standard sequential processing...")
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
                    print("   Continuing without outreach...")
                    outreach_stats = {'jobs_processed': 0, 'total_contacts_found': 0, 'total_emails_sent': 0, 'jobs_with_contacts': 0}
            except Exception as e:
                print(f"❌ Error creating resume PDF: {e}")
                print("   Continuing without outreach...")
                outreach_stats = {'jobs_processed': 0, 'total_contacts_found': 0, 'total_emails_sent': 0, 'jobs_with_contacts': 0}
        else:
            # Initialize and run outreach campaign
            await outreach_processor.initialise()
            
            outreach_stats = await outreach_processor.run(
                job_ids=None,  # Process all eligible jobs
                resume_text=resume_text,
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
        print(f"\n📈 Overall Campaign Statistics:")
        print(f"   Total Contacts in Database: {outreach_stats.get('total_contacts', 0)}")
        print(f"   Total Outreach Attempts: {outreach_stats.get('total_outreach', 0)}")
        print(f"   Companies Contacted: {outreach_stats.get('companies_contacted', 0)}")
        
        if outreach_stats.get('top_companies'):
            print(f"\n🏢 Top Companies Contacted:")
            for company, count in outreach_stats.get('top_companies', [])[:5]:
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
        await job_processor.close()
        await job_processor.scraper.close()
        await outreach_processor.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Comprehensive Job Search and Outreach System"
    )
    parser.add_argument(
        "--async-mode", "-a",
        action="store_true",
        help="Use AsyncJobPipeline for high-performance processing"
    )
    args = parser.parse_args()
    
    asyncio.run(main(use_async=args.async_mode))

