from anthropic import Anthropic, AsyncAnthropic
from typing import Dict
from src.config import settings
import json
import re

class ClaudeService:
    """Handle all AI operations using Anthropic Claude"""
    
    def __init__(self):
        # Use async client to integrate with the app's async pipeline
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model or "claude-3-5-sonnet-latest"

    async def _call_claude(self, prompt: str, max_tokens: int) -> str:
        """Call Anthropic with graceful fallback on model-not-found errors."""
        model_candidates = [
            self.model,
            "claude-3-5-sonnet-latest",
            "claude-3-haiku-20240307",
        ]
        last_err = None
        for m in model_candidates:
            try:
                message = await self.client.messages.create(
                    model=m,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                )
                # Remember a working model for subsequent calls
                self.model = m
                return message.content[0].text
            except Exception as e:
                # If the error indicates model not found, try next candidate
                last_err = e
                err_str = str(e)
                if "not_found_error" in err_str or "model:" in err_str:
                    continue
                # For other errors, break fast
                break
        # If all candidates failed, re-raise last error
        raise last_err if last_err else RuntimeError("Unknown Anthropic error")
    
    def _extract_json_from_response(self, text: str) -> dict:
        """Extract JSON from Claude response"""
        clean_text = re.sub(r'```json\n|\n```|```', '', text).strip()
        json_match = re.search(r'\{.*\}', clean_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        return {}
    
    async def extract_skills(self, job_description: str) -> Dict:
        """Extract required skills from job description"""
        
        prompt = f"""Analyze this job description and extract information in JSON format.

Job Description:
{job_description[:3000]}

Provide your response as a JSON object with exactly this structure:
{{
    "technical_skills": ["skill1", "skill2", "skill3"],
    "soft_skills": ["skill1", "skill2"],
    "experience_level": "Junior/Mid/Senior",
    "key_responsibilities": ["responsibility1", "responsibility2"]
}}

Return ONLY the JSON object, no additional text."""
        
        try:
            response_text = await self._call_claude(prompt, max_tokens=1024)
            result = self._extract_json_from_response(response_text)
            
            return {
                "technical_skills": result.get("technical_skills", []),
                "soft_skills": result.get("soft_skills", []),
                "experience_level": result.get("experience_level", "Unknown"),
                "key_responsibilities": result.get("key_responsibilities", [])
            }
        except Exception as e:
            print(f"❌ Error extracting skills: {e}")
            return {
                "technical_skills": [],
                "soft_skills": [],
                "experience_level": "Unknown",
                "key_responsibilities": []
            }
    
    async def match_resume_to_job(self, resume: str, job_skills: Dict) -> Dict:
        """Calculate match score between resume and job"""
        
        prompt = f"""Compare this resume with the job requirements and provide a match analysis.

Resume:
{resume[:2000]}

Job Requirements:
- Technical Skills: {', '.join(job_skills.get('technical_skills', []))}
- Soft Skills: {', '.join(job_skills.get('soft_skills', []))}
- Experience Level: {job_skills.get('experience_level', 'N/A')}

Provide your response as a JSON object with exactly this structure:
{{
    "match_score": 75,
    "matched_skills": ["skill1", "skill2"],
    "missing_skills": ["skill3", "skill4"],
    "recommendations": "Brief recommendation text"
}}

The match_score should be a number from 0 to 100.
Return ONLY the JSON object, no additional text."""
        
        try:
            response_text = await self._call_claude(prompt, max_tokens=1024)
            result = self._extract_json_from_response(response_text)
            
            return {
                "match_score": result.get("match_score", 0),
                "matched_skills": result.get("matched_skills", []),
                "missing_skills": result.get("missing_skills", []),
                "recommendations": result.get("recommendations", "")
            }
        except Exception as e:
            print(f"❌ Error matching resume: {e}")
            return {
                "match_score": 0,
                "matched_skills": [],
                "missing_skills": [],
                "recommendations": ""
            }
    
    async def rewrite_resume(self, original_resume: str, job_description: str) -> str:
        """Rewrite resume tailored to specific job"""
        
        prompt = f"""You are an expert resume writer. Rewrite this resume to better match the job description below.

IMPORTANT INSTRUCTIONS:
- Keep all information truthful and factual
- Emphasize relevant experience and skills
- Use keywords from the job description
- Maintain professional formatting
- Keep the same career history but highlight relevant aspects

Original Resume:
{original_resume[:3000]}

Job Description:
{job_description[:2000]}

Provide the rewritten resume in a professional format. Start directly with the resume content."""
        
        try:
            text = await self._call_claude(prompt, max_tokens=2048)
            return text.strip()
        except Exception as e:
            print(f"❌ Error rewriting resume: {e}")
            return original_resume
    
    async def generate_cover_letter(self, resume: str, job_description: str, company: str) -> str:
        """Generate personalized cover letter"""
        
        prompt = f"""Write a compelling, professional cover letter for this job application.

INSTRUCTIONS:
- Address why I'm interested in this specific role
- Highlight 2-3 most relevant experiences from my resume
- Show enthusiasm for the company
- Keep it concise (300-400 words)
- Professional but personable tone
- Do NOT include placeholder addresses or dates - start with "Dear Hiring Manager,"

My Resume:
{resume[:2000]}

Job Description:
{job_description[:2000]}

Company: {company}

Write the cover letter now:"""
        
        try:
            text = await self._call_claude(prompt, max_tokens=1536)
            return text.strip()
        except Exception as e:
            print(f"❌ Error generating cover letter: {e}")
            return f"Dear Hiring Manager,\n\nI am writing to express my interest in the position at {company}..."
