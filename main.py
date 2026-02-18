from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from src.job_processor import JobProcessor
from src.database import init_db
from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str

app = FastAPI()

# Add CORS for n8n Cloud
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB once at startup
@app.on_event("startup")
async def startup_event():
    init_db()
    print("✅ Database initialized")

@app.get("/")
async def root():
    return {"status": "healthy", "service": "Job Search API"}

@app.post("/run-query")
async def run_query(request: QueryRequest):
    """Run job search for a specific query"""

    processor = None
    try:
        processor = JobProcessor()

        # Step 1: Fetch jobs
        print(f"🔍 Fetching jobs for: {request.query}")
        jobs_count = await processor.fetch_and_store_jobs(query=request.query)

        # Step 2: Choose resume
        resume_path = "data/resume.txt"

        if "react" in request.query.lower():
            react_path = "data/resume_react.txt"
            if os.path.exists(react_path):
                resume_path = react_path

        elif "python" in request.query.lower():
            python_path = "data/resume_python.txt"
            if os.path.exists(python_path):
                resume_path = python_path

        # Check if resume exists
        if not os.path.exists(resume_path):
            raise HTTPException(
                status_code=404,
                detail=f"Resume file not found: {resume_path}"
            )

        # Read resume
        with open(resume_path, "r") as f:
            resume_text = f.read()

        # Step 3: Process jobs
        print(f"🤖 Processing jobs with min score 50...")
        await processor.process_all_jobs(resume_text, min_score=50)

        return {
            "status": "success",
            "query": request.query,
            "jobs_fetched": jobs_count,
            "resume_used": resume_path
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up
        if processor:
            try:
                processor.close()
                if hasattr(processor, 'scraper') and processor.scraper:
                    await processor.scraper.close()
            except:
                pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)