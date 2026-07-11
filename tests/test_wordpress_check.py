from unittest.mock import AsyncMock, patch

import pytest

from app.checks.wordpress import WordPressChecker
from app.models.incident import CheckType, Incident
from app.models.site import Site, SiteType

URL = "https://example.com"


class _FakeResponse:
    def __init__(self, status: int, payload: dict | None = None):
        self.status = status
        self._payload = payload or {}

    async def json(self, content_type=None):
        return self._payload


class _FakeGetContextManager:
    def __init__(self, response: _FakeResponse | None = None, exc: Exception | None = None):
        self._response = response
        self._exc = exc

    async def __aenter__(self) -> _FakeResponse:
        if self._exc is not None:
            raise self._exc
        return self._response

    async def __aexit__(self, *exc_info) -> bool:
        return False


class _FakeSession:
    def __init__(self, response: _FakeResponse):
        self._response = response

    def get(self, url, headers=None, timeout=None):
        return _FakeGetContextManager(response=self._response)


@pytest.fixture
def site(db):
    s = Site(
        name="Site",
        url=URL,
        expected_domain="example.com",
        type=SiteType.wordpress,
        mu_plugin_token="secret-token",
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


async def test_404_opens_wp_unreachable_incident(db, site):
    checker = WordPressChecker()
    http = _FakeSession(_FakeResponse(404))

    with patch("app.notifiers.telegram.send_incident_open", new_callable=AsyncMock) as mock_send:
        outcome = await checker.run(site, db, http)

    assert outcome.success is False
    incident = (
        db.query(Incident)
        .filter(Incident.site_id == site.id, Incident.check_type == CheckType.wp_unreachable)
        .first()
    )
    assert incident is not None
    assert incident.closed_at is None
    assert "mu-plugin not installed" in incident.cause
    mock_send.assert_called_once()


async def test_success_closes_wp_unreachable_incident(db, site):
    checker = WordPressChecker()

    with patch("app.notifiers.telegram.send_incident_open", new_callable=AsyncMock):
        await checker.run(site, db, _FakeSession(_FakeResponse(404)))

    report = {
        "core_version": "6.5",
        "core_update_available": None,
        "php_version": "8.2",
        "plugins": [],
        "themes": [],
        "admin_usernames": ["admin"],
    }
    with patch("app.notifiers.telegram.send_incident_close", new_callable=AsyncMock) as mock_close:
        outcome = await checker.run(site, db, _FakeSession(_FakeResponse(200, report)))

    assert outcome.success is True
    incident = (
        db.query(Incident)
        .filter(Incident.site_id == site.id, Incident.check_type == CheckType.wp_unreachable)
        .first()
    )
    assert incident.closed_at is not None
    mock_close.assert_called_once()


async def test_captures_mu_plugin_version_from_report(db, site):
    checker = WordPressChecker()
    report = {
        "mu_plugin_version": "1.1.0",
        "core_version": "6.5",
        "core_update_available": None,
        "php_version": "8.2",
        "plugins": [],
        "themes": [],
        "admin_usernames": ["admin"],
    }
    await checker.run(site, db, _FakeSession(_FakeResponse(200, report)))

    from app.models.wp_snapshot import WpSnapshot

    snapshot = db.query(WpSnapshot).filter(WpSnapshot.site_id == site.id).first()
    assert snapshot.mu_plugin_version == "1.1.0"


async def test_missing_mu_plugin_version_is_none(db, site):
    # Older mu-plugin copies (pre-version-reporting) simply won't have the key.
    checker = WordPressChecker()
    report = {
        "core_version": "6.5",
        "php_version": "8.2",
        "plugins": [],
        "themes": [],
        "admin_usernames": ["admin"],
    }
    await checker.run(site, db, _FakeSession(_FakeResponse(200, report)))

    from app.models.wp_snapshot import WpSnapshot

    snapshot = db.query(WpSnapshot).filter(WpSnapshot.site_id == site.id).first()
    assert snapshot.mu_plugin_version is None


async def test_500_with_not_configured_body_gives_specific_reason(db, site):
    # Mirrors the real Victoria Fones case: mu-plugin file present and returning
    # 500, but SITEWATCH_TOKEN was never defined in wp-config.php. Should not be
    # mistaken for a generic site-wide 500 -- the reason should point straight
    # at the actual missing setup step.
    checker = WordPressChecker()
    body = {"code": "sitewatch_not_configured", "message": "SITEWATCH_TOKEN is not defined in wp-config.php"}
    http = _FakeSession(_FakeResponse(500, body))

    with patch("app.notifiers.telegram.send_incident_open", new_callable=AsyncMock):
        await checker.run(site, db, http)

    incident = (
        db.query(Incident)
        .filter(Incident.site_id == site.id, Incident.check_type == CheckType.wp_unreachable)
        .first()
    )
    assert "SITEWATCH_TOKEN is not defined in wp-config.php" in incident.cause


async def test_401_with_unauthorized_body_gives_specific_reason(db, site):
    checker = WordPressChecker()
    body = {"code": "sitewatch_unauthorized", "message": "Invalid or missing X-SiteWatch-Token header"}
    http = _FakeSession(_FakeResponse(401, body))

    with patch("app.notifiers.telegram.send_incident_open", new_callable=AsyncMock):
        await checker.run(site, db, http)

    incident = (
        db.query(Incident)
        .filter(Incident.site_id == site.id, Incident.check_type == CheckType.wp_unreachable)
        .first()
    )
    assert "token mismatch" in incident.cause


async def test_unrelated_500_falls_back_to_generic_reason(db, site):
    checker = WordPressChecker()
    http = _FakeSession(_FakeResponse(500, {}))

    with patch("app.notifiers.telegram.send_incident_open", new_callable=AsyncMock):
        await checker.run(site, db, http)

    incident = (
        db.query(Incident)
        .filter(Incident.site_id == site.id, Incident.check_type == CheckType.wp_unreachable)
        .first()
    )
    assert "HTTP 500" in incident.cause


async def test_cve_incident_closes_once_plugin_is_patched(db, site):
    # Regression: wp_cve incidents were only ever opened, never closed -- once a
    # plugin's CVE alert fired it stayed "open" forever even after the site
    # updated past the patched version, since nothing re-evaluated it.
    checker = WordPressChecker()
    outdated_report = {
        "core_version": "6.5",
        "core_update_available": None,
        "php_version": "8.2",
        "plugins": [{"slug": "wpvivid-backuprestore", "installed": "0.9.129", "available": "0.9.130"}],
        "themes": [],
        "admin_usernames": ["admin"],
    }
    vulns = [{"title": "WPvivid Backup & Migration < 0.9.130 - Admin+ Arbitrary Directory Deletion"}]
    with patch("app.notifiers.telegram.send_incident_open", new_callable=AsyncMock), patch(
        "app.checks.wpscan_client.get_plugin_vulnerabilities", new_callable=AsyncMock, return_value=vulns
    ):
        await checker.run(site, db, _FakeSession(_FakeResponse(200, outdated_report)))

    open_incident = (
        db.query(Incident).filter(Incident.site_id == site.id, Incident.check_type == CheckType.wp_cve).first()
    )
    assert open_incident is not None
    assert open_incident.closed_at is None

    patched_report = {**outdated_report, "plugins": [{"slug": "wpvivid-backuprestore", "installed": "0.9.130", "available": "0.9.130"}]}
    with patch("app.notifiers.telegram.send_incident_close", new_callable=AsyncMock) as mock_close:
        await checker.run(site, db, _FakeSession(_FakeResponse(200, patched_report)))

    db.refresh(open_incident)
    assert open_incident.closed_at is not None
    mock_close.assert_called_once()


async def test_cve_incident_stays_open_when_wpscan_lookup_is_uncertain(db, site):
    # If WPScan can't be queried this run (budget exhausted, API down), that must
    # NOT be treated as "confirmed clean" -- a real open incident should stay open
    # rather than silently auto-closing just because we didn't get to check today.
    checker = WordPressChecker()
    outdated_report = {
        "core_version": "6.5",
        "core_update_available": None,
        "php_version": "8.2",
        "plugins": [{"slug": "wpvivid-backuprestore", "installed": "0.9.129", "available": "0.9.130"}],
        "themes": [],
        "admin_usernames": ["admin"],
    }
    vulns = [{"title": "some CVE"}]
    with patch("app.notifiers.telegram.send_incident_open", new_callable=AsyncMock), patch(
        "app.checks.wpscan_client.get_plugin_vulnerabilities", new_callable=AsyncMock, return_value=vulns
    ):
        await checker.run(site, db, _FakeSession(_FakeResponse(200, outdated_report)))

    open_incident = (
        db.query(Incident).filter(Incident.site_id == site.id, Incident.check_type == CheckType.wp_cve).first()
    )
    assert open_incident is not None

    with patch("app.checks.wpscan_client.get_plugin_vulnerabilities", new_callable=AsyncMock, return_value=None):
        await checker.run(site, db, _FakeSession(_FakeResponse(200, outdated_report)))

    db.refresh(open_incident)
    assert open_incident.closed_at is None


async def test_missing_token_is_not_an_incident(db, site):
    site.mu_plugin_token = None
    db.commit()

    checker = WordPressChecker()
    outcome = await checker.run(site, db, http=None)

    assert outcome.success is True
    assert db.query(Incident).count() == 0
