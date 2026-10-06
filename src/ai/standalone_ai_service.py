"""
standalone_ai_service.py — Dedicated AI Resume Parsing & Tailoring Microservice.
Exposes ATS PDF parsing, semantic skill matching, and personalization on Port 8003.
"""
import os
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.resume_parser import SharpAPIResumeParser

app = FastAPI(
    title="AI Resume & ATS Intelligence Service",
    description="ATS Parsing, Skill Taxonomy Extraction, and Tailoring Pipeline",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

parser = SharpAPIResumeParser()


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "ai-resume-service"}


@app.post("/api/resume/parse")
async def parse_resume_endpoint(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Empty resume file uploaded")
        profile = await parser.parse_resume(contents, filename=file.filename or "resume.pdf")
        return profile
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8003"))
    uvicorn.run(app, host="0.0.0.0", port=port)
