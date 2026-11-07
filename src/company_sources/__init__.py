"""Company sources: curated company lists and the miners that turn them into jobs/contacts.

- ``registries/``: static or CSV-backed company lists (Tier 1, Nifty 500, S&P 500,
  Shark Tank, accelerators, startups.gallery, ...). Pure data, no network.
- ``miners/``: per-registry engines that scrape careers pages and map decision makers.
  All share ``miners.base_company_miner``. Outreach stays draft-only unless the caller
  passes ``auto_send`` (see CLAUDE.md section 1).
"""
