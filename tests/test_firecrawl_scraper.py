"""Tests for src/scrapers/firecrawl_scraper.py."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.scrapers.firecrawl_scraper import (
    TOP_INDIAN_STARTUPS,
    FirecrawlCareerScraper,
)


# ---------------------------------------------------------------------------
# Registry sanity checks
# ---------------------------------------------------------------------------


class TestCompanyRegistry:
    """The registry itself should be well-formed — this is the thing most
    likely to silently rot (typo'd URL, duplicate entry) without a test."""

    def test_registry_has_around_100_companies(self):
        assert 90 <= len(TOP_INDIAN_STARTUPS) <= 110

    def test_no_duplicate_company_names(self):
        names = [name for name, _url in TOP_INDIAN_STARTUPS]
        assert len(names) == len(set(names))

    def test_all_entries_have_https_urls(self):
        for name, url in TOP_INDIAN_STARTUPS:
            assert url.startswith("https://"), f"{name} has a non-https URL: {url}"

    def test_all_entries_are_name_url_pairs(self):
        for entry in TOP_INDIAN_STARTUPS:
            assert len(entry) == 2
            name, url = entry
            assert isinstance(name, str) and name
            assert isinstance(url, str) and url


# ---------------------------------------------------------------------------
# Scraper behavior (Firecrawl API mocked — no real network calls)
# ---------------------------------------------------------------------------


@pytest.fixture
def scraper():
    s = FirecrawlCareerScraper(api_key="fc-test-key")
    yield s


class TestNoApiKey:
    """Without a key, the scraper should short-circuit rather than error."""

    @pytest.mark.asyncio
    async def test_search_returns_empty_without_api_key(self):
        s = FirecrawlCareerScraper(api_key=None)
        result = await s.search(query="engineer")
        assert result == []
        await s.close()


class TestScrapeUrl:
    """_scrape_url should parse Firecrawl's structured extraction response."""

    @pytest.mark.asyncio
    async def test_structured_extraction_parsed(self, scraper):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "json": {
                    "jobs": [
                        {"title": "Backend Engineer", "location": "Bengaluru",
                         "department": "Engineering", "url": "https://example.com/jobs/1"},
                        {"title": "Product Manager", "location": "Remote"},
                    ]
                },
                "markdown": "",
            }
        }
        with patch.object(scraper._http, "post", new=AsyncMock(return_value=mock_response)):
            jobs = await scraper._scrape_url("ExampleCo", "https://example.com/careers")

        assert len(jobs) == 2
        assert jobs[0]["title"] == "Backend Engineer"
        assert jobs[0]["company"] == "ExampleCo"
        assert jobs[0]["location"] == "Bengaluru"
        assert jobs[1]["location"] == "Remote"

    @pytest.mark.asyncio
    async def test_falls_back_to_markdown_when_extraction_empty(self, scraper):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "json": {"jobs": []},
                "markdown": "Join us! [Senior Data Engineer](https://example.com/jobs/42) "
                            "in Mumbai. Also check our [About Us](https://example.com/about) page.",
            }
        }
        with patch.object(scraper._http, "post", new=AsyncMock(return_value=mock_response)):
            jobs = await scraper._scrape_url("ExampleCo", "https://example.com/careers")

        titles = [j["title"] for j in jobs]
        assert "Senior Data Engineer" in titles
        assert "About Us" not in titles  # doesn't match job-title heuristics

    @pytest.mark.asyncio
    async def test_non_200_returns_empty(self, scraper):
        mock_response = MagicMock()
        mock_response.status_code = 404
        with patch.object(scraper._http, "post", new=AsyncMock(return_value=mock_response)):
            jobs = await scraper._scrape_url("ExampleCo", "https://example.com/careers")
        assert jobs == []

    @pytest.mark.asyncio
    async def test_request_exception_returns_empty(self, scraper):
        import httpx
        with patch.object(
            scraper._http, "post", new=AsyncMock(side_effect=httpx.ConnectError("boom"))
        ):
            jobs = await scraper._scrape_url("ExampleCo", "https://example.com/careers")
        assert jobs == []


class TestSearchFiltering:
    """search() should apply query/location filters and normalize output."""

    @pytest.mark.asyncio
    async def test_query_filters_by_title(self, scraper):
        async def fake_scrape_one_company(company, url, query, location):
            jobs = [
                {"title": "Backend Engineer", "company": company},
                {"title": "Sales Executive", "company": company},
            ]
            if query:
                jobs = [j for j in jobs if query.lower() in j["title"].lower()]
            return jobs

        with patch.object(scraper, "_scrape_one_company", side_effect=fake_scrape_one_company):
            jobs = await scraper.search(
                query="engineer",
                companies=[("TestCo", "https://testco.com/careers")],
            )

        assert len(jobs) == 1
        assert jobs[0]["title"] == "Backend Engineer"

    @pytest.mark.asyncio
    async def test_one_company_failing_does_not_break_others(self, scraper):
        async def fake_scrape_one_company(company, url, query, location):
            if company == "BrokenCo":
                raise RuntimeError("simulated failure")
            return [{"title": "Engineer", "company": company}]

        with patch.object(scraper, "_scrape_one_company", side_effect=fake_scrape_one_company):
            jobs = await scraper.search(
                companies=[
                    ("BrokenCo", "https://broken.example/careers"),
                    ("GoodCo", "https://good.example/careers"),
                ],
            )

        assert len(jobs) == 1
        assert jobs[0]["company"] == "GoodCo"


class TestDiscoverCarearsUrl:
    """Fallback rediscovery via Firecrawl search when the guessed URL is stale."""

    @pytest.mark.asyncio
    async def test_prefers_career_or_job_url(self, scraper):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"url": "https://example.com/blog/hiring-news"},
                {"url": "https://example.com/careers/open-roles"},
            ]
        }
        with patch.object(scraper._http, "post", new=AsyncMock(return_value=mock_response)):
            url = await scraper._discover_careers_url("ExampleCo")

        assert url == "https://example.com/careers/open-roles"

    @pytest.mark.asyncio
    async def test_no_results_returns_none(self, scraper):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        with patch.object(scraper._http, "post", new=AsyncMock(return_value=mock_response)):
            url = await scraper._discover_careers_url("ExampleCo")
        assert url is None


@pytest.mark.asyncio
async def test_close_does_not_raise(scraper):
    await scraper.close()
