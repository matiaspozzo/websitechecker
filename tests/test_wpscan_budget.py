from datetime import date, timedelta
from unittest.mock import patch

import pytest

from app.checks import wpscan_client
from app.models.config import GlobalConfig


@pytest.fixture(autouse=True)
def _clear_cache():
    wpscan_client._cache.clear()
    yield
    wpscan_client._cache.clear()


@pytest.fixture(autouse=True)
def _wpscan_key():
    with patch("app.checks.wpscan_client.settings.wpscan_api_key", "test-key"):
        yield


def test_reserve_budget_allows_up_to_limit(db):
    config = db.get(GlobalConfig, 1)
    config.wpscan_daily_limit = 3
    config.wpscan_requests_today = 0
    config.wpscan_requests_date = date.today().isoformat()
    db.commit()

    assert wpscan_client._reserve_budget(config, db) is True
    assert wpscan_client._reserve_budget(config, db) is True
    assert wpscan_client._reserve_budget(config, db) is True
    assert wpscan_client._reserve_budget(config, db) is False

    db.refresh(config)
    assert config.wpscan_requests_today == 3


def test_reserve_budget_resets_on_new_day(db):
    config = db.get(GlobalConfig, 1)
    config.wpscan_daily_limit = 1
    config.wpscan_requests_today = 1
    config.wpscan_requests_date = (date.today() - timedelta(days=1)).isoformat()
    db.commit()

    assert wpscan_client._reserve_budget(config, db) is True
    db.refresh(config)
    assert config.wpscan_requests_today == 1
    assert config.wpscan_requests_date == date.today().isoformat()


async def test_exhausted_budget_skips_request_without_raising(db):
    config = db.get(GlobalConfig, 1)
    config.wpscan_daily_limit = 0
    config.wpscan_requests_date = date.today().isoformat()
    db.commit()

    result = await wpscan_client.get_plugin_vulnerabilities(db, http=None, slug="some-plugin")

    assert result == []


async def test_cache_hit_does_not_consume_budget(db):
    config = db.get(GlobalConfig, 1)
    config.wpscan_daily_limit = 5
    config.wpscan_requests_today = 0
    config.wpscan_requests_date = date.today().isoformat()
    db.commit()

    wpscan_client._cache["plugin:cached-plugin"] = (
        __import__("time").monotonic(),
        {"cached-plugin": {"vulnerabilities": [{"title": "cached CVE"}]}},
    )

    result = await wpscan_client.get_plugin_vulnerabilities(db, http=None, slug="cached-plugin")

    assert result == [{"title": "cached CVE"}]
    db.refresh(config)
    assert config.wpscan_requests_today == 0


class _FakeResponse:
    def __init__(self, status: int, payload: dict):
        self.status = status
        self._payload = payload

    async def json(self):
        return self._payload


class _FakeGetContextManager:
    def __init__(self, response, captured_headers: dict):
        self._response = response
        self._captured_headers = captured_headers

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, *exc_info):
        return False


class _FakeSession:
    """Records the Authorization header of the last .get() call so tests can
    assert which API key was actually used, without a real network call."""

    def __init__(self, response: _FakeResponse):
        self._response = response
        self.last_headers: dict | None = None

    def get(self, url, headers=None, timeout=None):
        self.last_headers = headers
        return _FakeGetContextManager(self._response, headers)


async def test_panel_api_key_takes_priority_over_env(db):
    # Previously wpscan_client only ever read settings.wpscan_api_key (.env),
    # never GlobalConfig.wpscan_api_key -- the panel's "WPScan API key" field
    # was silently a no-op. Set both; the panel value must win.
    config = db.get(GlobalConfig, 1)
    config.wpscan_api_key = "panel-key"
    config.wpscan_daily_limit = 5
    config.wpscan_requests_date = date.today().isoformat()
    db.commit()

    http = _FakeSession(_FakeResponse(200, {"some-plugin": {"vulnerabilities": []}}))
    await wpscan_client.get_plugin_vulnerabilities(db, http, slug="some-plugin")

    assert http.last_headers == {"Authorization": "Token token=panel-key"}


async def test_falls_back_to_env_key_when_panel_key_unset(db):
    config = db.get(GlobalConfig, 1)
    config.wpscan_daily_limit = 5
    config.wpscan_requests_date = date.today().isoformat()
    db.commit()

    http = _FakeSession(_FakeResponse(200, {"some-plugin": {"vulnerabilities": []}}))
    await wpscan_client.get_plugin_vulnerabilities(db, http, slug="some-plugin")

    assert http.last_headers == {"Authorization": "Token token=test-key"}
