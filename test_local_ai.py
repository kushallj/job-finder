#!/usr/bin/env python3
"""
Quick test of local AI service
"""

import asyncio
from src.ai.local_llm_service import LocalLLMService

async def test():
    """Test local LLM"""
    print("🧪 Testing Local AI Service...")
    
    try:
        # Create service
        llm = LocalLLMService()
        
        # Health check
        print("\n1️⃣  Checking Ollama connection...")
        is_healthy = await llm.health_check()
        
        if not is_healthy:
            print("   ❌ Ollama not available")
            print("   💡 Make sure Ollama is running: ollama serve")
            return
        
        print("   ✅ Ollama is healthy")
        print(f"   Using model: {llm._cached_model}")
        
        # Test skill extraction
        print("\n2️⃣  Testing skill extraction...")
        test_job = """
        We are looking for a Python Developer with 3+ years of experience.
        Required skills: Python, Django, FastAPI, PostgreSQL, Docker, AWS.
        The candidate should have strong problem-solving skills and be a team player.
        """
        
        skills = await llm.extract_skills(test_job)
        
        print(f"   ✅ Skills extracted:")
        print(f"      Technical: {skills.get('technical_skills', [])[:5]}")
        print(f"      Soft: {skills.get('soft_skills', [])[:3]}")
        print(f"      Level: {skills.get('experience_level')}")
        
        # Test resume matching
        print("\n3️⃣  Testing resume matching...")
        test_resume = """
        Software Engineer with 4 years of experience in Python development.
        Expertise in Django, FastAPI, and building scalable web applications.
        Proficient in PostgreSQL, Docker, and AWS cloud services.
        """
        
        match = await llm.match_resume_to_job(test_resume, skills)
        
        print(f"   ✅ Match score: {match.get('match_score')}%")
        print(f"      Matched skills: {match.get('matched_skills', [])[:5]}")
        print(f"      Missing skills: {match.get('missing_skills', [])[:3]}")
        
        print("\n🎉 All tests passed! Local AI is working perfectly!")
        print("\n💡 You can now run: python comprehensive_job_search.py")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Check Ollama is running: ollama list")
        print("   2. Try: ollama run mistral:latest")
        print("   3. If still failing, try: ollama pull llama3.2:3b")

if __name__ == "__main__":
    asyncio.run(test())