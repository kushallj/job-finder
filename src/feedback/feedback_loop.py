"""
feedback_loop.py — Nightly self-improving feedback orchestrator.

Runs nightly (triggered by scheduler.py or FastAPI lifespan).
Closes the loop between outreach outcomes and pipeline behavior.

Pipeline:
  MetricsCollector.collect(window=7days)
      ↓
  PatternMiner.mine(metrics, db)
      ↓
  AdaptiveOptimizer.adapt(metrics, patterns) → recommendations
      ↓
  DigestGenerator.generate(snapshot)  +  save_snapshot()
      ↓
  Hook weights + send time prefs updated in data/learning.db
      ↓
  HookGenerator reads updated weights next call (automatic)

Integration points:
  - FeedbackLoop.get_recommendations() → called by any component wanting
    the latest recommendations (e.g., dashboard API, OutreachOrchestrator)
  - FeedbackLoop.get_hook_weights()    → called by HookGenerator
  - FeedbackLoop.get_best_hours()      → called by SmartSendTimer
  - FeedbackLoop.run_once()            → called by scheduler nightly
  - FeedbackLoop.start() / stop()      → FastAPI lifespan hooks

FastAPI integration example:
    @app.on_event("startup")
    async def startup():
        feedback_loop.start()

    @app.get("/api/digest")
    async def get_digest():
        return feedback_loop.latest_digest_dict()
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .models import LearningSnapshot, OutreachMetrics, Recommendation
from .metrics_collector import MetricsCollector
from .pattern_miner import PatternMiner
from .adaptive_optimizer import AdaptiveOptimizer
from .digest_generator import DigestGenerator

log = logging.getLogger(__name__)

_LEARNING_DB    = Path("data/learning.db")
_NIGHTLY_HOUR   = 2    # 02:00 UTC — after US/EU business hours, before APAC
_METRICS_WINDOW = 7    # days of data for nightly analysis
_PATTERN_WINDOW = 30   # days of data for pattern mining (wider window)


class FeedbackLoop:
    """
    Self-improving feedback loop orchestrator.

    All DB operations run in ThreadPoolExecutor (synchronous SQLAlchemy).
    The async interface wraps them with run_in_executor.
    """

    def __init__(self, db_session_factory=None):
        self._db_factory     = db_session_factory
        self._metrics        = MetricsCollector()
        self._miner          = PatternMiner()
        self._optimizer      = AdaptiveOptimizer()
        self._digest_gen     = DigestGenerator()
        self._executor       = ThreadPoolExecutor(max_workers=1, thread_name_prefix="feedback")

        self._latest_snapshot: Optional[LearningSnapshot] = None
        self._latest_recs:     List[Recommendation]       = []
        self._bg_task:         Optional[asyncio.Task]     = None
        self._running:         bool                       = False

    # ── FastAPI lifecycle ──────────────────────────────────────────────────────

    def start(self) -> None:
        """Launch nightly background task. Call from FastAPI startup."""
        if self._bg_task and not self._bg_task.done():
            return
        self._running = True
        try:
            loop = asyncio.get_event_loop()
            self._bg_task = loop.create_task(self._nightly_loop())
            log.info("FeedbackLoop: nightly task started")
        except RuntimeError:
            log.warning("FeedbackLoop: no event loop — nightly loop not started")

    def stop(self) -> None:
        """Cancel background task. Call from FastAPI shutdown."""
        self._running = False
        if self._bg_task and not self._bg_task.done():
            self._bg_task.cancel()
            log.info("FeedbackLoop: nightly task cancelled")

    # ── On-demand run ──────────────────────────────────────────────────────────

    async def run_once(
        self,
        metrics_window: int = _METRICS_WINDOW,
        pattern_window: int = _PATTERN_WINDOW,
    ) -> LearningSnapshot:
        """
        Run full analysis cycle immediately (for testing or manual trigger).
        Returns the LearningSnapshot.
        """
        loop = asyncio.get_event_loop()
        snapshot = await loop.run_in_executor(
            self._executor,
            self._run_sync,
            metrics_window,
            pattern_window,
        )
        self._latest_snapshot = snapshot
        self._latest_recs     = snapshot.recommendations
        return snapshot

    # ── Recommendation accessors (used by other pipeline components) ───────────

    def get_recommendations(self) -> List[Recommendation]:
        """Latest actionable recommendations. Returns [] if not yet run."""
        return self._latest_recs

    def get_hook_weights(self) -> Dict[str, float]:
        """Learned hook weights for HookGenerator. 1.0 = unchanged."""
        return self._optimizer.get_hook_weights()

    def get_best_hours(self) -> Dict[str, float]:
        """Learned best send hours. Keys are str(hour), values are reply_rate."""
        return self._optimizer.get_best_send_hours()

    def latest_digest_dict(self) -> Optional[dict]:
        """Latest digest as structured dict for dashboard API."""
        if not self._latest_snapshot:
            return None
        return self._digest_gen.generate_dict(self._latest_snapshot)

    def latest_digest_markdown(self) -> str:
        """Latest digest as markdown string."""
        if not self._latest_snapshot:
            return "No digest available yet. Run FeedbackLoop.run_once() first."
        return self._latest_snapshot.digest_markdown

    # ── Nightly loop ───────────────────────────────────────────────────────────

    async def _nightly_loop(self) -> None:
        """Background task: sleep until 02:00 UTC, run analysis, repeat."""
        while self._running:
            try:
                seconds_until_2am = self._seconds_until_hour(_NIGHTLY_HOUR)
                log.info(
                    "FeedbackLoop: next run in %.0fh",
                    seconds_until_2am / 3600
                )
                await asyncio.sleep(seconds_until_2am)
                if self._running:
                    await self.run_once()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                log.exception("FeedbackLoop nightly run failed: %s", exc)
                await asyncio.sleep(3600)   # retry in 1 hour on error

    # ── Sync analysis core (runs in ThreadPoolExecutor) ────────────────────────

    def _run_sync(
        self,
        metrics_window: int,
        pattern_window: int,
    ) -> LearningSnapshot:
        log.info("FeedbackLoop: starting analysis cycle")
        t0 = time.monotonic()

        db_session = self._get_db_session()
        try:
            # Step 1: Collect metrics
            self._metrics = MetricsCollector(db_session)
            metrics = self._metrics.collect(window_days=metrics_window)

            # Step 2: Mine patterns
            patterns = self._miner.mine(metrics, db_session, window_days=pattern_window)

            # Step 3: Adapt pipeline
            recommendations = self._optimizer.adapt(metrics, patterns)
            self._optimizer.persist_recommendations(recommendations)

            # Step 4: Generate digest
            snapshot = LearningSnapshot(
                snapshot_date   = datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                metrics         = metrics,
                patterns        = patterns,
                recommendations = recommendations,
            )
            self._digest_gen.generate(snapshot)    # fills digest_markdown
            self._digest_gen.save_snapshot(snapshot)

            elapsed = time.monotonic() - t0
            log.info(
                "FeedbackLoop: cycle complete in %.1fs | %s | %d recs",
                elapsed, metrics.funnel_str(), len(recommendations),
            )
            return snapshot

        finally:
            if db_session:
                try:
                    db_session.close()
                except Exception:
                    pass

    # ── DB session factory ─────────────────────────────────────────────────────

    def _get_db_session(self):
        if self._db_factory:
            try:
                return self._db_factory()
            except Exception as exc:
                log.warning("FeedbackLoop: DB session failed: %s", exc)
        # Try default session
        try:
            from src.database import SessionLocal
            return SessionLocal()
        except Exception:
            return None

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _seconds_until_hour(target_hour: int) -> float:
        """Seconds until next occurrence of target_hour UTC."""
        now  = datetime.now(timezone.utc)
        secs = (target_hour - now.hour) * 3600 - now.minute * 60 - now.second
        if secs <= 0:
            secs += 24 * 3600   # already past, wait until tomorrow
        return float(secs)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_default_loop: Optional[FeedbackLoop] = None


def get_loop(db_session_factory=None) -> FeedbackLoop:
    """Return (or create) the default FeedbackLoop singleton."""
    global _default_loop
    if _default_loop is None:
        _default_loop = FeedbackLoop(db_session_factory)
    return _default_loop
