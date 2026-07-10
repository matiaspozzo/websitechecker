from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app import incident_manager
from app.models.incident import CheckType, Severity
from app.models.silence import Silence
from app.models.site import Site, SiteType


@pytest.fixture
def site(db):
    s = Site(name="Site", url="https://example.com", expected_domain="example.com", type=SiteType.laravel)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


async def test_open_incident_sends_notification(db, site):
    with patch("app.notifiers.telegram.send_incident_open", new_callable=AsyncMock) as mock_send:
        incident = await incident_manager.open_incident(
            db, site, CheckType.uptime, Severity.critical, cause="down"
        )
    assert incident.closed_at is None
    mock_send.assert_called_once()


async def test_repeated_open_does_not_renotify(db, site):
    with patch("app.notifiers.telegram.send_incident_open", new_callable=AsyncMock) as mock_send:
        first = await incident_manager.open_incident(db, site, CheckType.uptime, Severity.critical, cause="down")
        second = await incident_manager.open_incident(db, site, CheckType.uptime, Severity.critical, cause="still down")

    assert first.id == second.id
    assert second.cause == "still down"
    mock_send.assert_called_once()


async def test_close_incident_sets_closed_at_and_notifies(db, site):
    with patch("app.notifiers.telegram.send_incident_open", new_callable=AsyncMock):
        await incident_manager.open_incident(db, site, CheckType.uptime, Severity.critical, cause="down")

    with patch("app.notifiers.telegram.send_incident_close", new_callable=AsyncMock) as mock_close:
        closed = await incident_manager.close_incident(db, site, CheckType.uptime)

    assert closed is not None
    assert closed.closed_at is not None
    mock_close.assert_called_once()


async def test_close_incident_noop_when_none_open(db, site):
    result = await incident_manager.close_incident(db, site, CheckType.uptime)
    assert result is None


async def test_silence_suppresses_notification_but_writes_incident(db, site):
    db.add(Silence(site_id=site.id, until=datetime.now(timezone.utc) + timedelta(hours=1)))
    db.commit()

    with patch("app.notifiers.telegram.send_incident_open", new_callable=AsyncMock) as mock_send:
        incident = await incident_manager.open_incident(db, site, CheckType.uptime, Severity.critical, cause="down")

    assert incident.id is not None
    mock_send.assert_not_called()


async def test_ssl_threshold_crossing_only_notifies_on_new_threshold(db, site):
    with patch("app.notifiers.telegram.send_incident_open", new_callable=AsyncMock) as mock_send:
        # First check: 10 days remaining crosses the 14-day threshold.
        await incident_manager.maybe_alert_threshold_crossing(
            db, site, CheckType.ssl, Severity.warning, cause="10 days left",
            days_remaining=10, thresholds=[14, 7, 3],
        )
        assert mock_send.call_count == 1

        # Still within the 14-day bucket (8 days) -- no new threshold crossed, no re-notify.
        await incident_manager.maybe_alert_threshold_crossing(
            db, site, CheckType.ssl, Severity.warning, cause="8 days left",
            days_remaining=8, thresholds=[14, 7, 3],
        )
        assert mock_send.call_count == 1

        # Crosses the 7-day threshold -- notify again.
        await incident_manager.maybe_alert_threshold_crossing(
            db, site, CheckType.ssl, Severity.critical, cause="6 days left",
            days_remaining=6, thresholds=[14, 7, 3],
        )
        assert mock_send.call_count == 2


async def test_ssl_threshold_closes_when_renewed(db, site):
    with patch("app.notifiers.telegram.send_incident_open", new_callable=AsyncMock):
        await incident_manager.maybe_alert_threshold_crossing(
            db, site, CheckType.ssl, Severity.critical, cause="2 days left",
            days_remaining=2, thresholds=[14, 7, 3],
        )

    with patch("app.notifiers.telegram.send_incident_close", new_callable=AsyncMock) as mock_close:
        result = await incident_manager.maybe_alert_threshold_crossing(
            db, site, CheckType.ssl, Severity.warning, cause="renewed",
            days_remaining=90, thresholds=[14, 7, 3],
        )

    assert result is not None
    assert result.closed_at is not None
    mock_close.assert_called_once()
