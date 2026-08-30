from __future__ import annotations

import csv
import json
import os
import time
from pathlib import Path
from typing import List, Optional, Dict, Any

import httpx

from .models import ReferralProfile

PROXYCURL_SEARCH_URL = "https://nubela.co/proxycurl/api/search/person/"
DISK_CACHE_DIR = Path("cache/proxycurl")
DISK_CACHE_TTL = 86400  # 24 hours


class LinkedInClient:
    """
    LinkedIn profile search client.
    Searches via Proxycurl Person Search API when PROXYCURL_API_KEY is configured.
    Otherwise falls back to local sample CSV for offline development & tests.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (api_key or os.getenv("PROXYCURL_API_KEY", "")).strip() or None
        self._use_api = bool(self.api_key)
        self._sample_paths = [
            Path("data_examples/sample_profiles.csv"),
            Path("data/sample_profiles.csv"),
            Path("sample_profiles.csv"),
        ]

    @property
    def mode(self) -> str:
        return "proxycurl" if self._use_api else "csv"

    def search_by_company(self, company_name: str, limit: int = 50) -> List[ReferralProfile]:
        company_name = (company_name or "").strip()
        if not company_name:
            return []
        if self._use_api:
            return self._search_proxycurl(company_name, limit)
        return self._search_csv(company_name, limit)

    # ------------------------------------------------------------------
    # Disk cache helpers
    # ------------------------------------------------------------------

    def _cache_path(self, company_name: str, limit: int) -> Path:
        safe = company_name.lower().replace(" ", "_").replace("/", "_")
        return DISK_CACHE_DIR / f"{safe}_{limit}.json"

    def _read_disk_cache(self, company_name: str, limit: int) -> Optional[List[dict]]:
        path = self._cache_path(company_name, limit)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if time.time() - data.get("ts", 0) > DISK_CACHE_TTL:
                return None
            return data.get("profiles")
        except Exception:
            return None

    def _write_disk_cache(self, company_name: str, limit: int, profiles: List[dict]) -> None:
        try:
            DISK_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            path = self._cache_path(company_name, limit)
            path.write_text(json.dumps({"ts": time.time(), "profiles": profiles}, indent=2), encoding="utf-8")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Proxycurl implementation
    # ------------------------------------------------------------------

    def _search_proxycurl(self, company_name: str, limit: int) -> List[ReferralProfile]:
        cached_raw = self._read_disk_cache(company_name, limit)
        if cached_raw is not None:
            return [ReferralProfile(**p) for p in cached_raw]

        profiles: List[ReferralProfile] = []
        next_page: Optional[str] = None

        while len(profiles) < limit:
            params: dict = {
                "current_company_name": company_name,
                "page_size": min(10, limit - len(profiles)),
            }
            if next_page:
                params["next_page"] = next_page

            try:
                resp = httpx.get(
                    PROXYCURL_SEARCH_URL,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    params=params,
                    timeout=15.0,
                )
            except httpx.RequestError as e:
                raise RuntimeError(f"Network error calling Proxycurl: {e}") from e

            if resp.status_code == 401:
                raise RuntimeError("Proxycurl API key is invalid or expired.")
            if resp.status_code == 429:
                raise RuntimeError("Proxycurl rate limit hit. Please retry shortly.")
            if resp.status_code != 200:
                raise RuntimeError(f"Proxycurl returned HTTP {resp.status_code}: {resp.text[:200]}")

            data = resp.json()
            results = data.get("results") or []

            for item in results:
                p = self._parse_proxycurl_result(item, company_name)
                if p:
                    profiles.append(p)

            next_page = data.get("next_page")
            if not next_page or not results:
                break

        profiles = profiles[:limit]
        self._write_disk_cache(company_name, limit, [p.model_dump() for p in profiles])
        return profiles

    def _parse_proxycurl_result(self, item: dict, company_name: str) -> Optional[ReferralProfile]:
        pd = item.get("profile") or {}
        first = (pd.get("first_name") or "").strip()
        last = (pd.get("last_name") or "").strip()
        full = (pd.get("full_name") or f"{first} {last}").strip()
        if not full:
            return None

        parts = [pd.get("city"), pd.get("state"), pd.get("country_full_name") or pd.get("country")]
        location = ", ".join(p for p in parts if p) or None

        return ReferralProfile(
            full_name=full,
            first_name=first or None,
            last_name=last or None,
            headline=pd.get("headline") or None,
            title=pd.get("occupation") or None,
            company=company_name,
            location=location,
            linkedin_url=item.get("linkedin_profile_url") or None,
            source="api",
        )

    # ------------------------------------------------------------------
    # CSV fallback
    # ------------------------------------------------------------------

    def _find_sample_file(self) -> Optional[Path]:
        for p in self._sample_paths:
            if p.exists():
                return p
        return None

    def _search_csv(self, company_name: str, limit: int) -> List[ReferralProfile]:
        sample = self._find_sample_file()
        if not sample:
            return []

        company_candidates = ["company", "employer", "company_name", "org", "organization"]
        profiles: List[ReferralProfile] = []

        try:
            with sample.open(newline="", encoding="utf-8-sig") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    normalized = {k.strip().lower(): v for k, v in row.items() if k}
                    company_val = None
                    for cand in company_candidates:
                        if cand in normalized and normalized[cand]:
                            company_val = normalized[cand].strip()
                            break

                    if not company_val or company_name.lower() not in company_val.lower():
                        continue

                    full = (normalized.get("full_name") or normalized.get("name") or "").strip()
                    first = (normalized.get("first_name") or "").strip()
                    last = (normalized.get("last_name") or "").strip()
                    if not full:
                        full = f"{first} {last}".strip()
                    if not full:
                        continue

                    try:
                        mc = int(normalized.get("mutual_connections") or 0)
                    except (ValueError, TypeError):
                        mc = 0

                    profiles.append(ReferralProfile(
                        full_name=full,
                        first_name=first or None,
                        last_name=last or None,
                        headline=normalized.get("headline") or None,
                        title=normalized.get("title") or None,
                        company=company_val,
                        location=normalized.get("location") or None,
                        linkedin_url=normalized.get("linkedin_url") or None,
                        mutual_connections=mc,
                        source="csv",
                    ))
                    if len(profiles) >= limit:
                        break
        except Exception:
            return []

        return profiles


linkedin_client = LinkedInClient()
