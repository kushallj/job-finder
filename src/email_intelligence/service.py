from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.models import Contact, DiscoveredEmailCache
from .models import DiscoveredContact, EmailVerificationResult, SearchDork, EmailPermutation
from .domain_resolver import domain_resolver, DomainResolver
from .dorking_engine import dorking_engine, GoogleDorkingEngine
from .pattern_synthesizer import pattern_synthesizer, CorporatePatternSynthesizer
from .github_harvester import github_harvester, GitHubAuthorHarvester
from .verifier import email_verifier, EmailVerifier
from .persona_scorer import persona_scorer, PersonaScorer

log = logging.getLogger(__name__)


class EmailIntelligenceService:
    """
    Orchestrates the complete Email Intelligence & Discovery Waterfall:
    Domain Resolution -> Dorking OSINT -> GitHub Commits -> Pattern Synthesis -> MX Verification -> CRM Ingestion.
    """

    def __init__(
        self,
        domain_res: Optional[DomainResolver] = None,
        dorker: Optional[GoogleDorkingEngine] = None,
        synthesizer: Optional[CorporatePatternSynthesizer] = None,
        harvester: Optional[GitHubAuthorHarvester] = None,
        verifier: Optional[EmailVerifier] = None,
    ):
        self.domain_resolver = domain_res or domain_resolver
        self.dorking_engine = dorker or dorking_engine
        self.pattern_synthesizer = synthesizer or pattern_synthesizer
        self.github_harvester = harvester or github_harvester
        self.verifier = verifier or email_verifier

    async def discover_company_decision_makers(
        self,
        db: Optional[Session],
        company: str,
        job_title: Optional[str] = None,
        website_hint: Optional[str] = None,
        target_name: Optional[str] = None,
        limit: int = 6,
    ) -> Dict[str, Any]:
        """
        Executes multi-layered waterfall discovery to identify verified engineering managers,
        tech recruiters, and founders with actionable emails.
        """
        company_clean = company.strip()
        domain = await self.domain_resolver.resolve_corporate_domain(company_clean, website_hint=website_hint)
        has_mx, mx_hosts, mail_provider = await self.domain_resolver.async_check_mx(domain)

        all_contacts: List[DiscoveredContact] = []
        seen_emails = set()

        # Step 1: Database Cache
        if db:
            cached = db.query(DiscoveredEmailCache).filter(
                func.lower(DiscoveredEmailCache.company) == company_clean.lower()
            ).limit(limit).all()
            for c in cached:
                if c.email not in seen_emails:
                    seen_emails.add(c.email)
                    all_contacts.append(DiscoveredContact(
                        name=c.person_name or "Engineering Leader",
                        title=c.title or "Engineering Leader",
                        company=company_clean,
                        domain=domain,
                        email=c.email,
                        confidence_score=c.confidence_score,
                        source=c.source or "cache",
                        mail_provider=c.mail_provider or mail_provider,
                        verified=c.verified,
                    ))

        # Step 2: Google Boolean Dorking OSINT
        if len(all_contacts) < limit:
            dorks = self.dorking_engine.generate_dorks(
                company=company_clean, domain=domain, person_name=target_name, role_title=job_title
            )
            for d in dorks[:2]:
                try:
                    dork_contacts = await self.dorking_engine.execute_dork_search(d.query, domain=domain, limit=3)
                    for dc in dork_contacts:
                        if dc.email not in seen_emails and self.verifier.is_valid_syntax(dc.email):
                            seen_emails.add(dc.email)
                            dc.company = company_clean
                            dc.mail_provider = mail_provider
                            all_contacts.append(dc)
                except Exception as exc:
                    log.debug("Dork search execution failed: %s", exc)

        # Step 3: GitHub Public Commits Harvester
        if len(all_contacts) < limit:
            try:
                gh_contacts = await self.github_harvester.search_company_engineers(company_clean, domain=domain, limit=3)
                for gc in gh_contacts:
                    if gc.email not in seen_emails and self.verifier.is_valid_syntax(gc.email):
                        seen_emails.add(gc.email)
                        gc.company = company_clean
                        gc.mail_provider = mail_provider
                        all_contacts.append(gc)
            except Exception as exc:
                log.debug("GitHub harvester search failed: %s", exc)

        # Step 4: Corporate Pattern Permutations for named person or default key roles
        if len(all_contacts) < limit:
            sample_names = [target_name] if target_name else [
                f"{company_clean} Engineering Manager",
                f"{company_clean} Talent Lead",
                f"{company_clean} Founder",
            ]
            for sname in sample_names:
                if not sname:
                    continue
                perms = self.pattern_synthesizer.generate_permutations(sname, domain=domain, has_mx=has_mx)
                if perms:
                    best_perm = perms[0]
                    if best_perm.email not in seen_emails:
                        seen_emails.add(best_perm.email)
                        title = "Engineering Manager" if "Manager" in sname else "Talent Acquisition" if "Talent" in sname else "Founder / CTO"
                        all_contacts.append(DiscoveredContact(
                            name=sname,
                            title=title,
                            company=company_clean,
                            domain=domain,
                            email=best_perm.email,
                            confidence_score=best_perm.confidence_score,
                            source="pattern_synthesis",
                            mail_provider=mail_provider,
                            verified=has_mx,
                        ))

        # Step 5: Rank by Persona Hierarchy
        ranked_contacts = PersonaScorer.rank_contacts(all_contacts)[:limit]

        # Step 6: Ingest & Cache
        if db:
            for rc in ranked_contacts:
                # Save to DiscoveredEmailCache
                existing_cache = db.query(DiscoveredEmailCache).filter(
                    DiscoveredEmailCache.email == rc.email
                ).first()
                if not existing_cache:
                    db.add(DiscoveredEmailCache(
                        company=rc.company,
                        domain=rc.domain or domain,
                        person_name=rc.name,
                        email=rc.email,
                        title=rc.title,
                        confidence_score=rc.confidence_score,
                        source=rc.source,
                        mail_provider=rc.mail_provider,
                        verified=rc.verified,
                    ))

                # Sync to Contact CRM
                existing_contact = db.query(Contact).filter(
                    Contact.email == rc.email
                ).first()
                if not existing_contact:
                    db.add(Contact(
                        name=rc.name,
                        company=rc.company,
                        title=rc.title,
                        email=rc.email,
                        confidence_score=int(rc.confidence_score),
                        source="email_intelligence",
                        found_at=datetime.utcnow(),
                    ))
            db.commit()

        return {
            "company": company_clean,
            "domain": domain,
            "has_mx": has_mx,
            "mail_provider": mail_provider,
            "total_found": len(ranked_contacts),
            "contacts": [c.model_dump() for c in ranked_contacts],
            "recommended_contact": ranked_contacts[0].model_dump() if ranked_contacts else None,
        }

    def verify_email(self, email: str) -> EmailVerificationResult:
        """Runs multi-factor deliverability and MX validation for an email."""
        return self.verifier.verify_email(email)

    def generate_dorks(
        self,
        company: str,
        domain: Optional[str] = None,
        person_name: Optional[str] = None,
        role_title: Optional[str] = None,
    ) -> List[SearchDork]:
        """Generates Google Boolean Search Dorks."""
        return self.dorking_engine.generate_dorks(company, domain, person_name, role_title)

    def generate_permutations(
        self,
        full_name: str,
        domain: str,
    ) -> List[EmailPermutation]:
        """Generates all 12 corporate permutations with live MX check."""
        has_mx, _, _ = self.domain_resolver.check_mx_records(domain)
        return self.pattern_synthesizer.generate_permutations(full_name, domain, has_mx=has_mx)


email_intelligence_service = EmailIntelligenceService()
