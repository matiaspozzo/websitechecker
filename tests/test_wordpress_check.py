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

    async def json(self):
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


async def test_missing_token_is_not_an_incident(db, site):
    site.mu_plugin_token = None
    db.commit()

    checker = WordPressChecker()
    outcome = await checker.run(site, db, http=None)

    assert outcome.success is True
    assert db.query(Incident).count() == 0
