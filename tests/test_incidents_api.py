from app.models.incident import CheckType, Incident, Severity
from app.models.site import Site, SiteType


def _make_site(db) -> Site:
    site = Site(name="Site", url="https://example.com", expected_domain="example.com", type=SiteType.wordpress)
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


def _make_incident(db, site: Site, *, closed: bool = False) -> Incident:
    from datetime import datetime, timezone

    incident = Incident(
        site_id=site.id,
        check_type=CheckType.wp_cve,
        severity=Severity.critical,
        cause="plugin 'x' has known CVEs",
        detail_json={},
        closed_at=datetime.now(timezone.utc) if closed else None,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


def test_acknowledge_sets_acknowledged_at(authed_client, db):
    site = _make_site(db)
    incident = _make_incident(db, site)

    resp = authed_client.post(f"/api/incidents/{incident.id}/acknowledge")

    assert resp.status_code == 200
    assert resp.json()["acknowledged_at"] is not None


def test_cannot_acknowledge_closed_incident(authed_client, db):
    site = _make_site(db)
    incident = _make_incident(db, site, closed=True)

    resp = authed_client.post(f"/api/incidents/{incident.id}/acknowledge")

    assert resp.status_code == 400


def test_unacknowledge_clears_acknowledged_at(authed_client, db):
    site = _make_site(db)
    incident = _make_incident(db, site)
    authed_client.post(f"/api/incidents/{incident.id}/acknowledge")

    resp = authed_client.post(f"/api/incidents/{incident.id}/unacknowledge")

    assert resp.status_code == 200
    assert resp.json()["acknowledged_at"] is None


def test_acknowledge_unknown_incident_404s(authed_client):
    resp = authed_client.post("/api/incidents/999999/acknowledge")
    assert resp.status_code == 404
