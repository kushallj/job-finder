from __future__ import annotations

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from .models import (
    IntelSourceType,
    CommunityIntelItem,
    CompanyCommunityIntel,
)
from .harvester import community_intel_harvester, CommunityIntelHarvester
from .synthesizer import community_intel_synthesizer, CommunityIntelSynthesizer

# In-memory cache for harvested company intel to prevent redundant calls
_INTEL_CACHE: Dict[str, CompanyCommunityIntel] = {}


class CommunityIntelService:
    """Orchestrates community intelligence gathering and synthesis."""

    def __init__(
        self,
        harvester: Optional[CommunityIntelHarvester] = None,
        synthesizer: Optional[CommunityIntelSynthesizer] = None,
    ):
        self.harvester = harvester or community_intel_harvester
        self.synthesizer = synthesizer or community_intel_synthesizer

    async def get_company_intel(
        self,
        company: str,
        role: str = "Software Engineer",
        force_refresh: bool = False,
    ) -> CompanyCommunityIntel:
        cache_key = f"{company.strip().lower()}:{role.strip().lower()}"
        if not force_refresh and cache_key in _INTEL_CACHE:
            return _INTEL_CACHE[cache_key]

        # Concurrently harvest from all sources
        tasks = [
            self.harvester.fetch_reddit_intel(company, role),
            self.harvester.fetch_hackernews_intel(company, role),
            self.harvester.fetch_medium_intel(company, role),
            self.harvester.fetch_substack_intel(company, role),
            self.harvester.fetch_youtube_mock_intel(company, role),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_sources: List[CommunityIntelItem] = []
        for r in results:
            if isinstance(r, list):
                all_sources.extend(r)

        synthesized = self.synthesizer.synthesize(company, role, all_sources)
        _INTEL_CACHE[cache_key] = synthesized
        return synthesized


community_intel_service = CommunityIntelService()
