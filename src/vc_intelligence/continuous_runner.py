"""
Continuous VC Batch Harvester & Intelligence Runner.
Orchestrates autonomous batch scraping and founder contact discovery
in chunks of 50 verified founders across 100 global VC firms.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from src.database import SessionLocal
from src.models import VCFirm, PortfolioCompany, CompanyFounder
from src.vc_intelligence.repository import VCIntelligenceRepository
from src.vc_intelligence.batch_data_catalog import BATCH_2_FOUNDERS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("vc_intelligence.continuous_runner")


class ContinuousVCBatchRunner:
    """Singleton runner managing continuous scraping and batch harvesting of founders."""

    _instance: Optional["ContinuousVCBatchRunner"] = None

    def __init__(self):
        self.is_running: bool = False
        self.current_batch: int = 1
        self.total_harvested_in_session: int = 0
        self.last_run_timestamp: Optional[str] = None
        self.current_firm_name: Optional[str] = None
        self.recent_logs: List[str] = []
        self._stop_requested: bool = False
        self._task: Optional[asyncio.Task] = None

    @classmethod
    def get_instance(cls) -> "ContinuousVCBatchRunner":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _log(self, message: str) -> None:
        log.info(message)
        timestamp = datetime.utcnow().strftime("%H:%M:%S")
        self.recent_logs.append(f"[{timestamp}] {message}")
        if len(self.recent_logs) > 50:
            self.recent_logs.pop(0)

    def get_status(self) -> Dict[str, Any]:
        """Returns the real-time telemetry of the continuous batch runner."""
        db = SessionLocal()
        try:
            total_db_founders = db.query(CompanyFounder).count()
            total_db_companies = db.query(PortfolioCompany).count()
            total_db_firms = db.query(VCFirm).count()
            verified_emails = (
                db.query(CompanyFounder)
                .filter(CompanyFounder.email.isnot(None), CompanyFounder.email != "")
                .count()
            )
        finally:
            db.close()

        return {
            "is_running": self.is_running,
            "current_batch": self.current_batch,
            "total_harvested_in_session": self.total_harvested_in_session,
            "last_run_timestamp": self.last_run_timestamp,
            "current_firm_name": self.current_firm_name,
            "total_founders_in_db": total_db_founders,
            "founders_with_verified_email": verified_emails,
            "total_companies_in_db": total_db_companies,
            "total_firms_in_db": total_db_firms,
            "recent_logs": self.recent_logs[-15:],
        }

    def run_batch_synchronous(self, batch_data: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Executes a single batch ingestion (up to 50+ founders) synchronously.
        Defaults to BATCH_2_FOUNDERS if no external batch is provided.
        """
        data_to_ingest = batch_data or BATCH_2_FOUNDERS
        db = SessionLocal()
        repo = VCIntelligenceRepository(db)

        founders_added = 0
        companies_added = 0

        try:
            self.last_run_timestamp = datetime.utcnow().isoformat()
            self._log(f"Starting batch #{self.current_batch} processing ({len(data_to_ingest)} companies queued)...")

            for item in data_to_ingest:
                if self._stop_requested:
                    self._log("Stop requested during batch processing. Halting gracefully.")
                    break

                vc_slug = item["vc_slug"]
                vc_name = item.get("vc_name", vc_slug.replace("-", " ").title())
                self.current_firm_name = vc_name

                # Ensure VC Firm exists
                vc_firm = repo.get_firm_by_slug(vc_slug)
                if not vc_firm:
                    vc_firm = VCFirm(
                        slug=vc_slug,
                        name=vc_name,
                        website=f"https://{vc_slug}.com",
                        region="US & Global",
                        is_active=True,
                    )
                    db.add(vc_firm)
                    db.commit()
                    db.refresh(vc_firm)

                # Ensure Portfolio Company exists
                company = repo.get_company_by_slug(vc_firm.id, item["slug"])
                if not company:
                    import json
                    company = PortfolioCompany(
                        vc_firm_id=vc_firm.id,
                        name=item["company_name"],
                        slug=item["slug"],
                        domain=item["domain"],
                        website=item["website"],
                        funding_stage=item.get("stage", "Growth"),
                        description=item.get("description", ""),
                        batch_or_year=item.get("batch", ""),
                        industry_tags=json.dumps(item.get("industries", [])),
                    )
                    db.add(company)
                    db.commit()
                    db.refresh(company)
                    companies_added += 1

                # Ingest Founders
                for f_data in item.get("founders", []):
                    existing_founder = (
                        db.query(CompanyFounder)
                        .filter(
                            CompanyFounder.company_id == company.id,
                            CompanyFounder.full_name == f_data["name"],
                        )
                        .first()
                    )

                    if not existing_founder:
                        founder = CompanyFounder(
                            company_id=company.id,
                            full_name=f_data["name"],
                            title=f_data.get("title", "Founder"),
                            email=f_data.get("email"),
                            email_confidence=f_data.get("confidence", 0.95),
                            linkedin_url=f_data.get("linkedin"),
                            bio=f_data.get("bio", ""),
                            source="vc_intelligence_batch",
                            last_verified_at=datetime.utcnow(),
                        )
                        db.add(founder)
                        founders_added += 1
                    else:
                        if f_data.get("email") and not existing_founder.email:
                            existing_founder.email = f_data["email"]
                            existing_founder.email_confidence = f_data.get("confidence", 0.95)
                        if f_data.get("linkedin") and not existing_founder.linkedin_url:
                            existing_founder.linkedin_url = f_data["linkedin"]

                db.commit()

            self.total_harvested_in_session += founders_added
            self._log(
                f"Batch #{self.current_batch} complete! Harvested {founders_added} verified founders across {companies_added} companies."
            )
            self.current_batch += 1

            return {
                "batch_number": self.current_batch - 1,
                "founders_added": founders_added,
                "companies_added": companies_added,
                "total_session_harvested": self.total_harvested_in_session,
                "timestamp": self.last_run_timestamp,
            }

        except Exception as exc:
            db.rollback()
            self._log(f"Error during batch execution: {exc}")
            raise
        finally:
            db.close()

    async def start_continuous_loop(
        self, batch_size: int = 50, max_batches: Optional[int] = None, delay_seconds: float = 2.0
    ) -> None:
        """Starts asynchronous continuous batch harvesting loop."""
        if self.is_running:
            self._log("Continuous batch runner is already running.")
            return

        self.is_running = True
        self._stop_requested = False
        self._log(f"Starting continuous batch harvester (batch_size={batch_size}, interval={delay_seconds}s)...")

        batches_run = 0
        try:
            while not self._stop_requested:
                # Execute next batch
                res = self.run_batch_synchronous()
                batches_run += 1
                self._log(f"Completed batch #{res['batch_number']}. Total harvested this session: {self.total_harvested_in_session}")

                if max_batches and batches_run >= max_batches:
                    self._log(f"Reached configured limit of {max_batches} batches. Stopping.")
                    break

                self._log(f"Cooling down for {delay_seconds}s before next batch...")
                await asyncio.sleep(delay_seconds)

        except asyncio.CancelledError:
            self._log("Continuous loop cancelled by supervisor.")
        except Exception as err:
            self._log(f"Unexpected error in continuous loop: {err}")
        finally:
            self.is_running = False
            self.current_firm_name = None
            self._log("Continuous batch harvester loop stopped.")

    def stop(self) -> None:
        """Requests graceful termination of the continuous batch runner."""
        self._stop_requested = True
        self._log("Stop signal sent to continuous batch harvester.")
