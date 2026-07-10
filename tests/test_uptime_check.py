from unittest.mock import AsyncMock, patch

import pytest

from app.checks import fetch as fetch_module
from app.checks.fetch import fetch_with_retry
from app.checks.uptime import UptimeChecker
from app.models.incident import CheckType, Incident, Severity
from app.models.site import Site, SiteType

URL = "https://example.com/"


class _FakeResponse:
    def __init__(self, status: int, body: str = "", url: str = URL, history: tuple = ()):
        self.status = status
        self._body = body
        self.url = url
        self.history = history

    async def text(self, errors: str = "strict") -> str:
        return self._body


class _FakeGetContextManager:
    """Mimics aiohttp's request context manager without depending on real aiohttp
    internals or a third-party mock library (aioresponses lags behind aiohttp
    releases and breaks on newer aiohttp's ClientResponse signature)."""

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
    """Queue of canned responses/exceptions, consumed in order by each .get() call."""

    def __init__(self, items: list):
        self._items = list(items)

    def get(self, url: str, allow_redirects: bool = True) -> _FakeGetContextManager:
        item = self._items.pop(0)
        if isinstance(item, Exception):
            return _FakeGetContextManager(exc=item)
        return _FakeGetContextManager(response=item)


@pytest.fixture
def site(db):
    s = Site(name="Site", url=URL, expected_domain="example.com", type=SiteType.laravel)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@pytest.fixture
def no_sleep():
    with patch("app.checks.fetch.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        yield mock_sleep


async def test_fetch_succeeds_without_retry(no_sleep):
    session = _FakeSession([_FakeResponse(200, body="ok")])
    result = await fetch_with_retry(session, URL)

    assert result.ok is True
    assert result.status == 200
    no_sleep.assert_not_called()


async def test_fetch_retries_then_succeeds(no_sleep):
    session = _FakeSession([_FakeResponse(503), _FakeResponse(200, body="ok")])
    result = await fetch_with_retry(session, URL)

    assert result.ok is True
    no_sleep.assert_called_once_with(5)


async def test_fetch_gives_up_after_all_retries(no_sleep):
    session = _FakeSession([_FakeResponse(503) for _ in range(4)])
    result = await fetch_with_retry(session, URL)

    assert result.ok is False
    assert result.error == "HTTP 503"
    assert no_sleep.call_args_list == [((5,),), ((15,),), ((30,),)]


async def test_uptime_checker_opens_incident_on_failure(db, site):
    checker = UptimeChecker()
    failure = fetch_module.FetchResult(ok=False, error="Connection refused")
    with (
        patch("app.checks.uptime.fetch_with_retry", new_callable=AsyncMock, return_value=failure),
        patch("app.notifiers.telegram.send_incident_open", new_callable=AsyncMock) as mock_send,
    ):
        outcome = await checker.run(site, db, http=None)

    assert outcome.success is False
    incident = db.query(Incident).filter(Incident.site_id == site.id, Incident.check_type == CheckType.uptime).first()
    assert incident is not None
    assert incident.closed_at is None
    mock_send.assert_called_once()


async def test_uptime_checker_closes_incident_on_recovery(db, site):
    db.add(Incident(site_id=site.id, check_type=CheckType.uptime, severity=Severity.critical, cause="was down"))
    db.commit()

    checker = UptimeChecker()
    success = fetch_module.FetchResult(ok=True, status=200, latency_ms=80)
    with (
        patch("app.checks.uptime.fetch_with_retry", new_callable=AsyncMock, return_value=success),
        patch("app.notifiers.telegram.send_incident_close", new_callable=AsyncMock) as mock_send,
    ):
        outcome = await checker.run(site, db, http=None)

    assert outcome.success is True
    incident = db.query(Incident).filter(Incident.site_id == site.id, Incident.check_type == CheckType.uptime).first()
    assert incident.closed_at is not None
    mock_send.assert_called_once()
