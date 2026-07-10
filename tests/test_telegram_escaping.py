from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.models.incident import CheckType, Incident, Severity
from app.models.site import Site, SiteType
from app.notifiers import telegram


@pytest.fixture
def site(db):
    s = Site(name="Site", url="https://example.com", expected_domain="example.com", type=SiteType.wordpress)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


async def test_incident_open_escapes_html_special_chars_in_cause(db, site):
    # Real case: WPScan vulnerability titles routinely contain "<=" / ">=" for
    # version ranges (e.g. "Advanced Custom Fields <= 3.5.1 - Remote File
    # Inclusion"), which Telegram's HTML parse_mode chokes on as an invalid
    # tag if not escaped -- this was silently crashing CVE alert delivery.
    incident = Incident(
        site_id=site.id,
        check_type=CheckType.wp_cve,
        severity=Severity.critical,
        cause="Plugin <= 3.5.1 - Remote File Inclusion & other <script>bad</script> stuff",
        opened_at=datetime.now(timezone.utc),
    )

    with patch("app.notifiers.telegram.send_message", new_callable=AsyncMock) as mock_send:
        await telegram.send_incident_open(incident, site)

    sent_text = mock_send.call_args.args[0]
    assert "<= 3.5.1" not in sent_text
    assert "&lt;= 3.5.1" in sent_text
    assert "<script>" not in sent_text
    assert "&amp;" in sent_text


async def test_incident_open_escapes_html_special_chars_in_site_name(db):
    site = Site(
        name="Bob's <Widgets> & Co",
        url="https://example.com",
        expected_domain="example.com",
        type=SiteType.wordpress,
    )
    incident = Incident(
        site_id=1,
        check_type=CheckType.uptime,
        severity=Severity.critical,
        cause="down",
        opened_at=datetime.now(timezone.utc),
    )

    with patch("app.notifiers.telegram.send_message", new_callable=AsyncMock) as mock_send:
        await telegram.send_incident_open(incident, site)

    sent_text = mock_send.call_args.args[0]
    assert "<Widgets>" not in sent_text
    assert "&lt;Widgets&gt;" in sent_text
