from unittest.mock import AsyncMock, patch

import pytest

from app.checks import fetch as fetch_module
from app.checks.uptime import UptimeChecker
from app.models.site import Site, SiteType


@pytest.fixture
def site(db):
    s = Site(name="Site", url="https://example.com", expected_domain="example.com", type=SiteType.laravel)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


async def test_repeated_failed_checks_send_one_alert(db, site):
    """Three consecutive failed check ticks for the same site+check_type must
    produce exactly one Telegram message, not one per tick."""
    checker = UptimeChecker()
    failure = fetch_module.FetchResult(ok=False, error="Connection refused")

    with (
        patch("app.checks.uptime.fetch_with_retry", new_callable=AsyncMock, return_value=failure),
        patch("app.notifiers.telegram.send_message", new_callable=AsyncMock) as mock_send,
    ):
        for _ in range(3):
            await checker.run(site, db, http=None)

    assert mock_send.call_count == 1


async def test_recovery_after_repeated_failures_sends_exactly_one_recovery_message(db, site):
    checker = UptimeChecker()
    failure = fetch_module.FetchResult(ok=False, error="Connection refused")
    success = fetch_module.FetchResult(ok=True, status=200, latency_ms=42)

    with patch("app.notifiers.telegram.send_message", new_callable=AsyncMock) as mock_send:
        with patch("app.checks.uptime.fetch_with_retry", new_callable=AsyncMock, return_value=failure):
            for _ in range(2):
                await checker.run(site, db, http=None)

        with patch("app.checks.uptime.fetch_with_retry", new_callable=AsyncMock, return_value=success):
            await checker.run(site, db, http=None)
            # A second success tick (already recovered) must not send another recovery message.
            await checker.run(site, db, http=None)

    assert mock_send.call_count == 2  # one "down" alert, one "recovered" alert


async def test_telegram_send_message_noop_without_token():
    from app.notifiers.telegram import send_message

    # TELEGRAM_BOT_TOKEN is unset in the test environment (see conftest.py);
    # this must log and return rather than raising.
    await send_message("test message")
