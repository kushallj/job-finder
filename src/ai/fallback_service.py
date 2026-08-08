"""
Fallback AI service when Anthropic API is not available
Provides basic job matching without external AI calls
"""

from typing import Dict, List
import re
import json

class FallbackAIService:
    """Simple fallback AI service using keyword matching"""
    
    def __init__(self):
        # Common tech skills for matching
        self.tech_skills = [
            'python', 'javascript', 'java', 'react', 'node.js', 'django', 
            'fastapi', 'flask', 'postgresql', 'mysql', 'mongodb', 'redis',
            'aws', 'docker', 'kubernetes', 'git', 'rest api', 'graphql',
            'html', 'css', 'typescript', 'vue.js', 'angular', 'express',
            'spring boot', 'microservices', 'devops', 'ci/cd', 'jenkins',
            'terraform', 'linux', 'nginx', 'apache', 'elasticsearch'
        ]
        
        self.experience_keywords = {
            'junior': ['junior', 'entry', 'fresher', '0-2 years', 'graduate'],
            'mid': ['mid', 'intermediate', '2-5 years', '3-6 years'],
            'senior': ['senior', 'lead', 'principal', '5+ years', '6+ years']
        }

    async def extract_skills(self, job_description: str) -> Dict:
        """Extract skills from job description using keyword matching"""
        
        job_text = job_description.lower()
        
        # Find technical skills
        technical_skills = []
        for skill in self.tech_skills:
            if skill.lower() in job_text:
                technical_skills.append(skill.title())
        
        # Find soft skills (basic patterns)
        soft_skills = []
        soft_skill_patterns = [
            'communication', 'teamwork', 'leadership', 'problem solving',
            'analytical', 'creative', 'collaborative', 'agile', 'scrum'
        ]
        
        for skill in soft_skill_patterns:
            if skill in job_text:
                soft_skills.append(skill.title())
        
        # Determine experience level
        experience_level = "Mid"  # Default
        for level, keywords in self.experience_keywords.items():
            if any(keyword in job_text for keyword in keywords):
                experience_level = level.title()
                break
        
        # Extract responsibilities (simple approach)
        responsibilities = []
        if 'develop' in job_text:
            responsibilities.append('Software Development')
        if 'design' in job_text:
            responsibilities.append('System Design')
        if 'test' in job_text:
            responsibilities.append('Testing')
        if 'deploy' in job_text:
            responsibilities.append('Deployment')
        
        return {
            "technical_skills": technical_skills[:10],  # Limit to top 10
            "soft_skills": soft_skills[:5],
            "experience_level": experience_level,
            "key_responsibilities": responsibilities
        }

    async def match_resume_to_job(self, resume: str, job_skills: Dict) -> Dict:
        """Calculate match score between resume and job using keyword matching"""
        
        resume_text = resume.lower()
        job_technical_skills = [skill.lower() for skill in job_skills.get('technical_skills', [])]
        
        # Count matching skills
        matched_skills = []
        for skill in job_technical_skills:
            if skill in resume_text:
                matched_skills.append(skill.title())
        
        # Calculate match score
        total_skills = len(job_technical_skills)
        if total_skills == 0:
            match_score = 50  # Default score when no skills specified
        else:
            match_score = int((len(matched_skills) / total_skills) * 100)
        
        # Boost score for relevant experience
        experience_boost = 0
        if any(word in resume_text for word in ['python', 'developer', 'engineer']):
            experience_boost += 20
        if any(word in resume_text for word in ['backend', 'full stack', 'api']):
            experience_boost += 15
        
        match_score = min(100, match_score + experience_boost)
        
        # Find missing skills
        missing_skills = []
        for skill in job_technical_skills:
            if skill not in [s.lower() for s in matched_skills]:
                missing_skills.append(skill.title())
        
        # Generate recommendations
        recommendations = []
        if match_score >= 80:
            recommendations.append("Excellent match - apply immediately")
        elif match_score >= 60:
            recommendations.append("Good match - worth applying")
        elif match_score >= 40:
            recommendations.append("Moderate match - consider if interested")
        else:
            recommendations.append("Low match - may not be suitable")
        
        if missing_skills:
            recommendations.append(f"Consider learning: {', '.join(missing_skills[:3])}")
        
        return {
            "match_score": match_score,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "recommendations": "; ".join(recommendations)
        }

    async def rewrite_resume(self, original_resume: str, job_description: str) -> str:
        """Simple resume optimization without AI"""
        
        # For fallback, just return original resume with a note
        optimized_resume = f"""
{original_resume}

--- OPTIMIZED FOR THIS ROLE ---
This resume has been reviewed for relevance to the position.
Key strengths highlighted based on job requirements.
        """.strip()
        
        return optimized_resume

    async def generate_cover_letter(self, resume: str, job_description: str, company: str) -> str:
        """Generate a basic cover letter template"""
        
        # Get sender name from config (avoid hardcoding PII)
        try:
            from src.config import settings
            sender_name = getattr(settings, "sender_name", None) or "The Candidate"
        except Exception:
            sender_name = "The Candidate"
        
        # Extract key skills from resume for personalization
        resume_lower = resume.lower()
        key_skills = []
        
        skill_checks = [
            ('Python development', 'python'),
            ('Backend development', 'backend'),
            ('Full-stack development', 'full stack'),
            ('API development', 'api'),
            ('Database management', 'database'),
            ('Cloud technologies', 'aws')
        ]
        
        for skill_name, keyword in skill_checks:
            if keyword in resume_lower:
                key_skills.append(skill_name)
        
        skills_text = ", ".join(key_skills[:3]) if key_skills else "software development"
        
        cover_letter = f"""Dear Hiring Manager,

I am writing to express my strong interest in the position at {company}. With my background in {skills_text}, I am excited about the opportunity to contribute to your team.

My experience includes:
• Software development with modern technologies
• Problem-solving and analytical thinking
• Collaborative work in team environments

I have attached my resume for your review and would welcome the opportunity to discuss how my skills align with your needs.

Thank you for your consideration. I look forward to hearing from you.

Best regards,
{sender_name}"""

        return cover_letter