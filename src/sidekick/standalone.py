"""
standalone.py — Standalone Microservice Runner for Ghost Copilot Sidekick Brain.
Hosts sub-microsecond Trie, Inverted Index RAG, and Local LLM endpoints on Port 8001.
"""
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.sidekick.api.sidekick_router import router as sidekick_router

app = FastAPI(
    title="Ghost Copilot Sidekick Brain Service",
    description="Sub-microsecond Radix Trie & Hybrid Inverted Index RAG Teleprompter Engine",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sidekick_router)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "sidekick-brain",
        "trie_ready": True
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
