from datetime import datetime, timezone

from app.models.incident import CheckType, Incident, Severity
from app.models.site import Site, SiteType


def _make_site(db) -> Site:
    site = Site(name="Site", url="https://example.com", expected_domain="example.com", type=SiteType.wordpress)
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


def test_acknowledged_wp_cve_excluded_from_dashboard_badges(authed_client, db):
    site = _make_site(db)
    db.add(
        Incident(
            site_id=site.id,
            check_type=CheckType.wp_cve,
            severity=Severity.critical,
            cause="plugin 'x' has known CVEs",
            detail_json={},
            acknowledged_at=datetime.now(timezone.utc),
        )
    )
    db.commit()

    resp = authed_client.get("/api/dashboard")

    assert resp.status_code == 200
    entry = next(s for s in resp.json()["sites"] if s["id"] == site.id)
    assert entry["vulnerable_plugin_count"] == 0
    assert entry["open_incident_count"] == 0


def test_unacknowledged_wp_cve_still_counted(authed_client, db):
    site = _make_site(db)
    db.add(
        Incident(
            site_id=site.id,
            check_type=CheckType.wp_cve,
            severity=Severity.critical,
            cause="plugin 'x' has known CVEs",
            detail_json={},
        )
    )
    db.commit()

    resp = authed_client.get("/api/dashboard")

    entry = next(s for s in resp.json()["sites"] if s["id"] == site.id)
    assert entry["vulnerable_plugin_count"] == 1
    assert entry["open_incident_count"] == 1
