"""Adapters in src/job_sources/sources: response mapping, auth, matching. No network
(httpx.MockTransport with payloads shaped like the real APIs, captured 2026-11-08)."""

import asyncio
import base64
import json

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.config import settings
from src.job_sources import JobRecord, SearchQuery, upsert_jobs
from src.job_sources.sources import _http, apis, ats, feeds, rss
from src.models import Base, Job

WWR_RSS = """<?xml version="1.0"?><rss version="2.0"><channel><title>WWR</title>
<item><title>Acme Corp: Senior Python Engineer</title><link>https://wwr.example/1</link>
<description>&lt;ul&gt;&lt;li&gt;Build APIs in Python&lt;/li&gt;&lt;/ul&gt;</description>
<pubDate>Mon, 02 Nov 2026 10:00:00 +0000</pubDate></item>
<item><title>Beta: Designer</title><link>https://wwr.example/2</link><description>Figma</description></item>
</channel></rss>"""


@pytest.fixture
def mock_http(monkeypatch):
    """Route requests to a handler per URL prefix; record what was sent."""
    routes, sent = {}, []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        for prefix, respond in routes.items():
            if str(request.url).startswith(prefix):
                return respond(request)
        return httpx.Response(404)

    monkeypatch.setattr(_http, "TRANSPORT", httpx.MockTransport(handler))
    return routes, sent


def run(coro):
    return asyncio.run(coro)


def test_rss_feed_splits_company_and_filters_by_query(mock_http):
    routes, _ = mock_http
    routes["https://weworkremotely.com/"] = lambda r: httpx.Response(200, text=WWR_RSS)
    wwr = next(s for s in rss.SOURCES if s.name == "weworkremotely")

    records = run(wwr.fetch(SearchQuery("python developer")))  # "developer" is optional
    assert [(r.company, r.title) for r in records] == [("Acme Corp", "Senior Python Engineer")]
    rec = records[0]
    assert rec.source == "weworkremotely" and rec.work_mode == "remote"
    assert "- Build APIs in Python" in rec.description
    assert rec.posted_date is not None


def test_ashby_maps_fields_and_skips_unlisted(mock_http, monkeypatch):
    routes, _ = mock_http
    monkeypatch.setattr(ats, "boards", lambda: {"ashby": {"linear": "Linear"}})
    routes["https://api.ashbyhq.com/"] = lambda r: httpx.Response(200, json={"jobs": [
        {"id": "a1", "title": "Backend Engineer", "team": "Eng", "location": "Europe", "isListed": True,
         "isRemote": True, "workplaceType": "Remote", "jobUrl": "https://jobs.ashbyhq.com/linear/a1",
         "descriptionPlain": "We use Python and Postgres", "publishedAt": "2026-10-01T00:00:00Z"},
        {"id": "a2", "title": "Python Engineer (hidden)", "isListed": False},
    ]})
    src = next(s for s in ats.SOURCES if s.name == "ashby")
    [rec] = run(src.fetch(SearchQuery("python")))
    assert (rec.company, rec.title, rec.work_mode, rec.has_remote) == ("Linear", "Backend Engineer", "remote", True)


def test_per_company_failures_are_skipped(mock_http, monkeypatch):
    routes, _ = mock_http
    monkeypatch.setattr(ats, "boards", lambda: {"recruitee": {"good": "Good Co", "gone": "Gone Co"}})
    routes["https://good.recruitee.com/"] = lambda r: httpx.Response(200, json={"offers": [
        {"id": 1, "title": "Data Engineer", "city": "Amsterdam", "country": "Netherlands",
         "careers_url": "https://good.example/1", "salary": {"min": 50000, "max": 70000, "currency": "EUR"}}]})
    src = next(s for s in ats.SOURCES if s.name == "recruitee")
    [rec] = run(src.fetch(SearchQuery("data")))
    assert (rec.company, rec.salary_min, rec.salary_currency) == ("Good Co", 50000.0, "EUR")


def test_reed_uses_basic_auth_and_parses_uk_dates(mock_http, monkeypatch):
    routes, sent = mock_http
    monkeypatch.setattr(settings, "reed_api_key", "reed-key")
    routes["https://www.reed.co.uk/"] = lambda r: httpx.Response(200, json={"results": [
        {"jobId": 7, "jobTitle": "Python Developer", "employerName": "Acme", "locationName": "London",
         "minimumSalary": 50000, "maximumSalary": 60000, "date": "03/11/2026", "jobUrl": "https://reed.example/7"}]})
    [rec] = run(next(s for s in apis.SOURCES if s.name == "reed").fetch(SearchQuery("python")))
    assert sent[0].headers["Authorization"] == "Basic " + base64.b64encode(b"reed-key:").decode()
    assert (rec.salary_min, rec.salary_currency, rec.posted_date.month) == (50000.0, "GBP", 11)


def test_jooble_posts_with_key_in_path(mock_http, monkeypatch):
    routes, sent = mock_http
    monkeypatch.setattr(settings, "jooble_api_key", "jk")
    routes["https://jooble.org/api/jk"] = lambda r: httpx.Response(200, json={"jobs": [
        {"id": 1, "title": "Go Engineer", "company": "Gopher", "location": "Remote", "snippet": "<b>Go</b> and k8s",
         "link": "https://jooble.example/1", "updated": "2026-11-01T00:00:00"}]})
    [rec] = run(next(s for s in apis.SOURCES if s.name == "jooble").fetch(SearchQuery("go")))
    assert sent[0].method == "POST" and json.loads(sent[0].content)["keywords"] == "go"
    assert rec.description == "Go and k8s"


def test_hn_whoishiring_parses_top_level_comments(mock_http):
    routes, _ = mock_http

    def algolia(request):
        if "search_by_date" in str(request.url):
            return httpx.Response(200, json={"hits": [{"objectID": "100", "title": "Ask HN: Who is hiring? (November 2026)"}]})
        return httpx.Response(200, json={"hits": [
            {"objectID": "1", "parent_id": 100, "comment_text": "Acme | Backend Engineer | Remote (EU)<p>Python, Go"},
            {"objectID": "2", "parent_id": 1, "comment_text": "a reply | not a job"},
            {"objectID": "3", "parent_id": 100, "comment_text": "No pipes here, just chatter"},
        ]})
    routes["https://hn.algolia.com/"] = algolia
    [rec] = run(next(s for s in feeds.SOURCES if s.name == "hn_whoishiring").fetch(SearchQuery("engineer")))
    assert (rec.company, rec.title, rec.location, rec.has_remote) == ("Acme", "Backend Engineer", "Remote (EU)", True)


def test_retries_transient_errors_then_succeeds(mock_http, monkeypatch):
    routes, sent = mock_http
    monkeypatch.setattr("tenacity.nap.time.sleep", lambda _s: None)
    calls = iter([httpx.Response(503), httpx.Response(200, json={"jobs": []})])
    routes["https://remotive.com/"] = lambda r: next(calls)
    assert run(next(s for s in feeds.SOURCES if s.name == "remotive").fetch(SearchQuery("x"))) == []
    assert len(sent) == 2


@pytest.mark.parametrize(("query", "text", "expected"), [
    ("python developer", "Senior Python Engineer", True),   # generic word optional
    ("python developer", "Senior Java Developer", False),   # specific word required
    ("senior engineer", "Platform Engineer", True),          # all-generic: any word
    ("software engineer", "Platform Engineer", False),      # "software" is specific
    ("c++", "Embedded C++ role", True),
    ("", "anything", True),
])
def test_matches(query, text, expected):
    assert _http.matches(query, text) is expected


def test_html_to_text_keeps_bullets():
    assert _http.html_to_text("<p>Intro</p><ul><li>One</li><li>Two</li></ul>").splitlines()[-2:] == ["- One", "- Two"]


def test_ssl_context_is_shared():
    assert _http.ssl_context() is _http.ssl_context()


def test_upsert_refreshes_and_merges_provider_sources():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    first = JobRecord.from_dict({"job_id": "x:1", "title": "Dev", "company": "Co"}, "remotive")
    again = JobRecord.from_dict({"job_id": "x:1", "title": "Dev", "company": "Co", "salary_min": 90000}, "remoteok")

    assert upsert_jobs(db, [first]) == (1, 0)
    assert upsert_jobs(db, [again]) == (0, 1)
    job = db.query(Job).one()
    assert job.salary_min == 90000 and json.loads(job.provider_sources) == ["remotive", "remoteok"]
