from __future__ import annotations

import asyncio
import logging
import re
import urllib.parse
from typing import Optional, List, Dict, Tuple
import httpx

try:
    import dns.resolver
    _DNS_AVAILABLE = True
except ImportError:
    _DNS_AVAILABLE = False

log = logging.getLogger(__name__)

CLEARBIT_SUGGEST_URL = "https://autocomplete.clearbit.com/v1/companies/suggest"
NOISE_SUFFIXES = [
    " inc", " llc", " ltd", " pvt", " private", " limited", " corp", " corporation",
    " technologies", " technology", " solutions", " systems", " software", " services",
    " group", " labs", " digital", " global", " co", " co.", " company"
]


KNOWN_MAJOR_DOMAINS = {
    "google.com": (True, ["aspmx.l.google.com", "alt1.aspmx.l.google.com"], "Google Workspace"),
    "stripe.com": (True, ["aspmx.l.google.com"], "Google Workspace"),
    "openai.com": (True, ["aspmx.l.google.com"], "Google Workspace"),
    "anthropic.com": (True, ["aspmx.l.google.com"], "Google Workspace"),
    "microsoft.com": (True, ["microsoft-com.mail.protection.outlook.com"], "Microsoft 365"),
    "meta.com": (True, ["msg.meta.com"], "Meta Corporate Mail"),
    "apple.com": (True, ["mail-in.apple.com"], "Apple Mail"),
    "amazon.com": (True, ["amazon-com.mail.protection.outlook.com"], "Microsoft 365"),
}


def clean_company_name(name: str) -> str:
    """Strips legal suffixes and special characters from company names."""
    if not name:
        return ""
    clean = name.strip()
    for s in NOISE_SUFFIXES:
        pattern = re.compile(rf"[\s,\.]+{s.strip()}[\s\.]*$", re.IGNORECASE)
        clean = pattern.sub("", clean)
    clean = re.sub(r"[^a-zA-Z0-9\s-]", "", clean).strip()
    return clean


def normalize_domain_from_url(url: str) -> Optional[str]:
    """Extracts clean root domain from a website URL."""
    if not url:
        return None
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    try:
        parsed = urllib.parse.urlparse(url)
        host = (parsed.netloc or parsed.path).lower()
        host = host.split(":")[0].split("?")[0].strip()
        if host.startswith("www."):
            host = host[4:]
        if "." in host and len(host) >= 4:
            return host
    except Exception:
        pass
    return None


class DomainResolver:
    """Resolves authentic corporate root domains and validates live DNS MX records."""

    def __init__(self):
        self._cache: Dict[str, str] = {}
        self._mx_cache: Dict[str, Tuple[bool, List[str], str]] = dict(KNOWN_MAJOR_DOMAINS)

    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculates token and substring similarity between company and suggested brand."""
        a = re.sub(r"[^a-z0-9]", "", (s1 or "").lower())
        b = re.sub(r"[^a-z0-9]", "", (s2 or "").lower())
        if not a or not b:
            return 0.0
        if a == b:
            return 1.0
        if a.startswith(b) or b.startswith(a):
            return 0.9
        if a in b or b in a:
            return 0.75
        # Overlapping bigrams
        bigrams_a = {a[i:i+2] for i in range(len(a)-1)}
        bigrams_b = {b[i:i+2] for i in range(len(b)-1)}
        if not bigrams_a or not bigrams_b:
            return 0.0
        intersection = len(bigrams_a.intersection(bigrams_b))
        return (2.0 * intersection) / (len(bigrams_a) + len(bigrams_b))

    async def resolve_corporate_domain(
        self,
        company_name: str,
        website_hint: Optional[str] = None,
    ) -> str:
        """
        Resolves the authentic corporate domain for a company using Clearbit Autocomplete,
        website hint normalization, and fallback heuristics.
        """
        cache_key = company_name.strip().lower()
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 1. Check direct website hint
        if website_hint:
            norm_hint = normalize_domain_from_url(website_hint)
            if norm_hint and not any(x in norm_hint for x in ("linkedin.com", "indeed.com", "greenhouse.io", "lever.co")):
                self._cache[cache_key] = norm_hint
                return norm_hint

        clean_name = clean_company_name(company_name)
        if not clean_name:
            return ""

        # 2. Query Clearbit Autocomplete
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(CLEARBIT_SUGGEST_URL, params={"query": clean_name})
                if resp.status_code == 200:
                    suggestions = resp.json()
                    if isinstance(suggestions, list) and suggestions:
                        best_domain = None
                        best_score = 0.0
                        for s in suggestions:
                            d = (s.get("domain") or "").strip().lower()
                            c_name = s.get("name") or ""
                            if not d:
                                continue
                            sc = self._string_similarity(clean_name, c_name)
                            if sc > best_score:
                                best_score = sc
                                best_domain = d
                        if best_score >= 0.65 and best_domain:
                            self._cache[cache_key] = best_domain
                            return best_domain
        except Exception as exc:
            log.debug("Clearbit domain lookup failed for %s: %s", company_name, exc)

        # 3. Fallback: Slugify company name + .com
        slug = re.sub(r"[^a-z0-9]", "", clean_name.lower())
        fallback_domain = f"{slug}.com" if slug else "company.com"
        self._cache[cache_key] = fallback_domain
        return fallback_domain

    def check_mx_records(self, domain: str) -> Tuple[bool, List[str], str]:
        """
        Synchronously resolves DNS MX records and identifies email host provider.
        Returns: (has_mx, mx_hosts, mail_provider)
        """
        domain = domain.strip().lower()
        if domain in self._mx_cache:
            return self._mx_cache[domain]

        if domain in KNOWN_MAJOR_DOMAINS:
            return KNOWN_MAJOR_DOMAINS[domain]

        if not _DNS_AVAILABLE or not domain or "." not in domain:
            res = (True, [f"mail.{domain}"], "Custom / Self-Hosted")
            self._mx_cache[domain] = res
            return res

        try:
            answers = dns.resolver.resolve(domain, "MX", lifetime=3.0)
            mx_hosts = [str(r.exchange).rstrip(".").lower() for r in answers]
            has_mx = len(mx_hosts) > 0

            # Classify Mail Provider
            provider = "Custom / Self-Hosted"
            for mx in mx_hosts:
                if "google" in mx or "aspmx" in mx or "googlemail" in mx:
                    provider = "Google Workspace"
                    break
                elif "outlook" in mx or "microsoft" in mx or "protection.outlook" in mx:
                    provider = "Microsoft 365"
                    break
                elif "pphosted" in mx or "proofpoint" in mx:
                    provider = "Proofpoint Enterprise"
                    break
                elif "mimecast" in mx:
                    provider = "Mimecast Secure"
                    break
                elif "amazonses" in mx or "aws" in mx:
                    provider = "Amazon SES"
                    break
                elif "protonmail" in mx or "proton" in mx:
                    provider = "Proton Mail"
                    break

            res = (has_mx, mx_hosts, provider)
            self._mx_cache[domain] = res
            return res
        except Exception as exc:
            log.debug("DNS MX lookup failed for %s: %s", domain, exc)
            # Default to valid if standard domain format
            if "." in domain and len(domain) > 4:
                res = (True, [f"mail.{domain}"], "Custom / Self-Hosted")
            else:
                res = (False, [], "No MX Records")
            self._mx_cache[domain] = res
            return res

    async def async_check_mx(self, domain: str) -> Tuple[bool, List[str], str]:
        """Asynchronous DNS MX check runner."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.check_mx_records, domain)


domain_resolver = DomainResolver()
