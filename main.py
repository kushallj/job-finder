import asyncio
import os
from src.job_processor import JobProcessor
from src.database import init_db

async def main():
    """Main entry point"""
    print("🚀 Job Automation System Starting...")

    # Initialize database
    init_db()

    # Create processor
    processor = JobProcessor()

    try:
        # Run for multiple queries with query-specific resumes when available
        queries = ["python developer", "react developer", "flutter developer", "node.js developer"]

        for q in queries:
            # Step 1: Fetch jobs for each query
            await processor.fetch_and_store_jobs(query=q)
            print("\n🔍 Step 1: Fetching jobs from all sources...")
            await processor.fetch_and_store_jobs(
                query=q,
                use_google=True  # Enable Google career page search
            )

            # Step 2: Load query-specific resume if present
            resume_path = "data/resume.txt"
            if "react" in q.lower():
                react_path = "data/resume_react.txt"
                if os.path.exists(react_path):
                    resume_path = react_path
            elif "python" in q.lower():
                py_path = "data/resume_python.txt"
                if os.path.exists(py_path):
                    resume_path = py_path

            with open(resume_path, "r") as f:
                resume_text = f.read()

            # Step 3: Process only remaining unprocessed jobs after this fetch
            await processor.process_all_jobs(resume_text, min_score=50)
        
        print("\n✅ All done!")
        
    finally:
        processor.close()
        await processor.scraper.close()

if __name__ == "__main__":
    asyncio.run(main())