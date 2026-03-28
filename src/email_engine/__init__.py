"""
src/email_engine — Advanced Email Discovery Engine

The Hunter.io algorithm, reverse-engineered and open-sourced for personal use.

Architecture (5 layers, DAG):

  Layer 1: Data Collection (all async, concurrent)
  ┌─────────────────────────────────────────────────────────────┐
  │  WebCrawler  │  GitHubMiner  │  ExistingProviders (12+)    │
  └─────────────────────────────────────────────────────────────┘
                              ↓
  Layer 2: Pattern Mining (Dynamic Programming)
  ┌─────────────────────────────────────────────────────────────┐
  │  PatternMiner — derives dominant email format per domain    │
  │  PatternDB    — SQLite persistence, O(1) lookup after first │
  └─────────────────────────────────────────────────────────────┘
                              ↓
  Layer 3: Candidate Generation
  ┌─────────────────────────────────────────────────────────────┐
  │  Generate all format permutations for known names          │
  │  Rank by pattern confidence                                 │
  └─────────────────────────────────────────────────────────────┘
                              ↓
  Layer 4: Verification (ThreadPoolExecutor — blocking I/O)
  ┌─────────────────────────────────────────────────────────────┐
  │  MX lookup → Catch-all detection → SMTP RCPT TO handshake  │
  └─────────────────────────────────────────────────────────────┘
                              ↓
  Layer 5: Confidence Scoring + Dedup + Rank
  ┌─────────────────────────────────────────────────────────────┐
  │  Multi-factor scorer: smtp×0.35 + pattern×0.25 + sources×0.20 │
  │  Cross-source corroboration boost                           │
  └─────────────────────────────────────────────────────────────┘
"""

from .github_miner import GitHubMiner
from .pattern_miner import PatternMiner, PatternDB
from .web_crawler import TeamPageCrawler
from .confidence_scorer import ConfidenceScorer, ScoringSignals
from .discovery_engine import EmailDiscoveryEngine

__all__ = [
    "GitHubMiner",
    "PatternMiner",
    "PatternDB",
    "TeamPageCrawler",
    "ConfidenceScorer",
    "ScoringSignals",
    "EmailDiscoveryEngine",
]
