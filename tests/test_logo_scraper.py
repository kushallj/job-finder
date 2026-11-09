"""Company logo scraping (src/vc_intelligence/logo_scraper.py). Offline: httpx.MockTransport."""

import asyncio
import json

import httpx

from src.vc_intelligence import logo_scraper as ls

HOMEPAGE = """<html><head>
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/brand.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-180.png" sizes="180x180">
<meta property="og:image" content="https://cdn.acme.test/social-banner.png">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Organization",
 "logo":{"@type":"ImageObject","url":"https://cdn.acme.test/logo.png"}}</script>
</head><body>Acme</body></html>"""


def test_candidates_ranked_jsonld_touch_icon_svg_icon_then_og_image():
    cands = ls.extract_candidates(HOMEPAGE, "https://acme.test/")
    assert [(c.source, c.url) for c in cands] == [
        ("jsonld", "https://cdn.acme.test/logo.png"),
        ("apple_touch_icon", "https://acme.test/apple-180.png"),
        ("icon", "https://acme.test/brand.svg"),       # SVG beats a 32px favicon
        ("icon", "https://acme.test/favicon.ico"),
        ("og_image", "https://cdn.acme.test/social-banner.png"),
    ]


def _client(routes):
    def handler(request: httpx.Request) -> httpx.Response:
        return routes.get(str(request.url), lambda: httpx.Response(404))()
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True)


def test_find_logo_skips_candidates_that_are_not_real_images():
    routes = {
        "https://acme.test": lambda: httpx.Response(200, text=HOMEPAGE, headers={"content-type": "text/html"}),
        "https://cdn.acme.test/logo.png": lambda: httpx.Response(404),                          # dead JSON-LD logo
        "https://acme.test/apple-180.png": lambda: httpx.Response(200, text="<html>", headers={"content-type": "text/html"}),
        "https://acme.test/brand.svg": lambda: httpx.Response(200, content=b"<svg xmlns='x'/>", headers={"content-type": "image/svg+xml"}),
    }

    async def go():
        async with _client(routes) as c:
            return await ls.find_logo(c, "acme.test")
    assert asyncio.run(go()) == {"logo_url": "https://acme.test/brand.svg", "source": "icon"}


def test_find_logo_falls_back_to_google_favicon_when_site_is_down():
    async def go():
        async with _client({}) as c:
            return await ls.find_logo(c, "gone.test")
    assert asyncio.run(go()) == {"logo_url": ls.google_favicon("gone.test"), "source": "google_favicon"}


def test_save_is_atomic_and_sorted(tmp_path):
    path = tmp_path / "logos.json"
    ls.save_logos({"b.test": {"logo_url": "u2", "source": "icon"}, "a.test": {"logo_url": "u1", "source": "jsonld"}}, path)
    assert list(json.loads(path.read_text(encoding="utf-8"))) == ["a.test", "b.test"]
    assert ls.load_logos(path)["a.test"]["logo_url"] == "u1"
    assert not path.with_suffix(".tmp").exists()


def test_importer_copies_logo_and_api_returns_it(monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from src.jobify.services.founders import company_ui
    from src.models import Base, PortfolioCompany
    from src.vc_intelligence import import_founder_data as imp

    monkeypatch.setattr(ls, "load_logos", lambda path=ls.LOGOS_FILE: {"acme.test": {"logo_url": "https://acme.test/logo.png", "source": "jsonld"}})
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        importer = imp.Importer(db)
        firm = importer.firm("test-vc", "Test VC")
        co = importer.company(firm, "Acme", "https://www.acme.test/about")
        other = importer.company(firm, "NoLogo", "nologo.test")
        db.commit()
        assert co.logo_url == "https://acme.test/logo.png"
        assert other.logo_url is None
        assert company_ui(co, [], firm, hiring=False, unlocked=False)["logo"] == "https://acme.test/logo.png"
        assert company_ui(other, [], firm, hiring=False, unlocked=False)["logo"] is None
        assert db.query(PortfolioCompany).count() == 2
