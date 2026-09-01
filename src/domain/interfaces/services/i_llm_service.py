"""
Domain Interface: ILLMService
Clean Architecture Port defining contract for AI analysis and text completion.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class ILLMService(ABC):
    """
    Abstract AI Provider interface supporting resume matching and email generation.
    """

    @abstractmethod
    async def generate_completion(
        self, prompt: str, system_instruction: Optional[str] = None
    ) -> str:
        """Generate textual completion from prompt."""
        pass

    @abstractmethod
    async def analyze_match(
        self, resume_text: str, job_description: str
    ) -> Dict[str, Any]:
        """
        Evaluate candidate-job fit score and skills breakdown.

        Returns:
            Dict containing match_score (0-100), key_strengths, and missing_skills.
        """
        pass
