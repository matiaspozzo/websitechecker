from unittest.mock import AsyncMock, patch

import pytest

from app.checks.content_integrity import ContentIntegrityChecker
from app.checks.fetch import FetchResult
from app.models.incident import CheckType
from app.models.site import Site, SiteType
from app.models.suspicious_pattern import SuspiciousPattern
from app.models.trusted_domain import TrustedDomain

CLEAN_HTML = "<html><body><h1>Welcome to Example</h1></body></html>"
EVAL_ATOB_HTML = "<script>eval(atob('ZG9jdW1lbnQ='))</script>"
UNKNOWN_IFRAME_HTML = '<iframe src="https://evil-attacker.example/payload"></iframe>'
EXTERNAL_META_REFRESH_HTML = '<meta http-equiv="refresh" content="0;url=https://evil-attacker.example/">'


@pytest.fixture
def site(db):
    s = Site(
        name="Site",
        url="https://example.com",
        expected_domain="example.com",
        type=SiteType.wordpress,
        expected_keyword="Welcome",
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@pytest.fixture(autouse=True)
def _seed_patterns(db):
    db.add(SuspiciousPattern(pattern="eval(atob(", is_regex=False, enabled=True))
    db.add(TrustedDomain(domain="googletagmanager.com", enabled=True))
    db.commit()


async def _run_with_body(site, db, body: str) -> bool:
    checker = ContentIntegrityChecker()
    fetch_result = FetchResult(ok=True, status=200, body=body, latency_ms=42, final_url=site.url)
    with (
        patch("app.checks.content_integrity.fetch_with_retry", new_callable=AsyncMock, return_value=fetch_result),
        patch("app.notifiers.telegram.send_incident_open", new_callable=AsyncMock),
        patch("app.notifiers.telegram.send_incident_close", new_callable=AsyncMock),
    ):
        outcome = await checker.run(site, db, http=None)
    return outcome.success


async def test_clean_page_has_no_false_positive(db, site):
    assert await _run_with_body(site, db, CLEAN_HTML) is True


async def test_known_benign_iframe_is_not_flagged(db, site):
    # Google Tag Manager, YouTube, Maps, etc. are extremely common on real
    # sites and must not trigger a "possible compromise" incident on their own.
    body = '<html><body>Welcome<iframe src="https://www.googletagmanager.com/ns.html?id=GTM-XXXX"></iframe></body></html>'
    assert await _run_with_body(site, db, body) is True


async def test_custom_trusted_domain_suppresses_iframe_flag(db, site):
    # A domain not in the seed defaults (e.g. a 360-tour host or a client's
    # own secondary domain) can be added from the panel to stop it being flagged.
    db.add(TrustedDomain(domain="kuula.co", description="360 tour embeds", enabled=True))
    db.commit()
    body = '<html><body>Welcome<iframe src="https://kuula.co/share/abc123"></iframe></body></html>'
    assert await _run_with_body(site, db, body) is True


async def test_disabled_trusted_domain_is_still_flagged(db, site):
    db.add(TrustedDomain(domain="kuula.co", enabled=False))
    db.commit()
    body = '<html><body>Welcome<iframe src="https://kuula.co/share/abc123"></iframe></body></html>'
    assert await _run_with_body(site, db, body) is False


async def test_missing_keyword_flags_content_incident(db, site):
    assert await _run_with_body(site, db, "<html><body>nothing relevant here</body></html>") is False


async def test_eval_atob_pattern_detected(db, site):
    assert await _run_with_body(site, db, "<html><body>Welcome" + EVAL_ATOB_HTML + "</body></html>") is False


async def test_unknown_iframe_domain_detected(db, site):
    assert await _run_with_body(site, db, "<html><body>Welcome" + UNKNOWN_IFRAME_HTML + "</body></html>") is False


async def test_external_meta_refresh_detected(db, site):
    assert await _run_with_body(site, db, EXTERNAL_META_REFRESH_HTML + "<body>Welcome</body>") is False


async def test_iframe_on_own_domain_is_not_flagged(db, site):
    body = '<html><body>Welcome<iframe src="https://example.com/widget"></iframe></body></html>'
    assert await _run_with_body(site, db, body) is True


async def test_redirect_to_unexpected_domain_flags_redirect_incident(db, site):
    checker = ContentIntegrityChecker()
    fetch_result = FetchResult(
        ok=True, status=200, body="Welcome", latency_ms=10, final_url="https://attacker.example/"
    )
    with (
        patch("app.checks.content_integrity.fetch_with_retry", new_callable=AsyncMock, return_value=fetch_result),
        patch("app.notifiers.telegram.send_incident_open", new_callable=AsyncMock) as mock_open,
        patch("app.notifiers.telegram.send_incident_close", new_callable=AsyncMock),
    ):
        outcome = await checker.run(site, db, http=None)

    assert outcome.success is False
    calls = [c.args[0].check_type for c in mock_open.call_args_list]
    assert CheckType.redirect in calls
