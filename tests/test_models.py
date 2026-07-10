from app.models.check_result import CheckResult
from app.models.incident import CheckType, Incident, Severity
from app.models.site import Site, SiteType


def _make_site(db, **overrides):
    defaults = dict(
        name="Test Site",
        url="https://example.com",
        expected_domain="example.com",
        type=SiteType.wordpress,
    )
    defaults.update(overrides)
    site = Site(**defaults)
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


def test_create_site(db):
    site = _make_site(db)
    assert site.id is not None
    assert site.active is True
    assert site.check_interval_seconds == 300


def test_site_relationships(db):
    site = _make_site(db)
    db.add(CheckResult(site_id=site.id, check_type=CheckType.uptime, success=True, latency_ms=120))
    db.add(Incident(site_id=site.id, check_type=CheckType.uptime, severity=Severity.critical, cause="down"))
    db.commit()
    db.refresh(site)

    assert len(site.check_results) == 1
    assert len(site.incidents) == 1


def test_delete_site_cascades(db):
    site = _make_site(db)
    db.add(CheckResult(site_id=site.id, check_type=CheckType.uptime, success=True, latency_ms=50))
    db.add(Incident(site_id=site.id, check_type=CheckType.uptime, severity=Severity.critical, cause="down"))
    db.commit()

    db.delete(site)
    db.commit()

    assert db.query(CheckResult).count() == 0
    assert db.query(Incident).count() == 0
