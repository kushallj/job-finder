from __future__ import annotations

from typing import Optional
from .models import ResumeGenerateRequest, CoverLetterGenerateRequest, ResumeDocumentResponse
from .generator import ats_resume_generator, ATSResumeGenerator


class ResumeGeneratorService:
    """Orchestrates ATS-compliant resume and cover letter synthesis."""

    def __init__(self, generator: Optional[ATSResumeGenerator] = None):
        self.generator = generator or ats_resume_generator

    def generate_resume(self, req: ResumeGenerateRequest) -> ResumeDocumentResponse:
        return self.generator.generate_ats_resume(req)

    def generate_cover_letter(self, req: CoverLetterGenerateRequest) -> ResumeDocumentResponse:
        return self.generator.generate_cover_letter(req)


resume_generator_service = ResumeGeneratorService()
