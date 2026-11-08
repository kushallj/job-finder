"""Every job source, grouped by how it gets data. Add a source to the right module's SOURCES.

  apis.py    official, key-based APIs (run when their keys are set)
  feeds.py   public JSON APIs, no key
  rss.py     RSS/Atom feeds, no key
  ats.py     ATS job boards (Greenhouse, Lever, Ashby, ...), companies in ../ats_boards.yml
  scrape.py  HTML scraping / crawlers: opt-in (JOB_SOURCES_ALLOW_SCRAPING)
"""

from src.job_sources.base import CallableSource
from src.job_sources.sources import apis, ats, feeds, rss, scrape
from src.job_sources.sources.scrape import JOBSPY_SITES

ALL_SOURCES: tuple[CallableSource, ...] = (*apis.SOURCES, *feeds.SOURCES, *rss.SOURCES, *ats.SOURCES, *scrape.SOURCES)

_names = [s.name for s in ALL_SOURCES]
if len(_names) != len(set(_names)):  # source name = provenance + JOB_SOURCES key; must be unique
    raise RuntimeError(f"duplicate job source names: {sorted({n for n in _names if _names.count(n) > 1})}")

__all__ = ["ALL_SOURCES", "JOBSPY_SITES"]
