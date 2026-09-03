"""
src/tsenta — Autonomous AI Career Agent & Auto-Apply Integration (YC S26 Compatibility Engine).

Provides:
- 18+ ATS classification (Workday, Greenhouse, Lever, Ashby, BambooHR, SmartRecruiters, Jobvite, Taleo, etc.)
- Tailored resume and cover letter synthesis
- Screening question resolution via Answer Bank in candidate's voice
- Human-in-the-loop review gates (Diff View)
- Verifiable cryptographic submission receipts & audit logs
- Quota tracking & multi-channel webhook dispatch
"""
from src.tsenta.ats_detector import detect_ats, ATSInfo, SUPPORTED_ATS_LIST
from src.tsenta.models import TsentaSubmission, TsentaQuota, TsentaConfigRecord
from src.tsenta.payload_builder import TsentaPayloadBuilder
from src.tsenta.client import TsentaClient
from src.tsenta.service import TsentaService

__all__ = [
    "detect_ats",
    "ATSInfo",
    "SUPPORTED_ATS_LIST",
    "TsentaSubmission",
    "TsentaQuota",
    "TsentaConfigRecord",
    "TsentaPayloadBuilder",
    "TsentaClient",
    "TsentaService",
]
