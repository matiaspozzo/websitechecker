import pytest
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app import scheduler
from app.models.site import MonitoringMode, Site, SiteType


@pytest.fixture(autouse=True)
def _clear_scheduler():
    for job in scheduler.scheduler.get_jobs():
        scheduler.scheduler.remove_job(job.id)
    yield
    for job in scheduler.scheduler.get_jobs():
        scheduler.scheduler.remove_job(job.id)


@pytest.fixture
def site(db):
    s = Site(
        name="Site", url="https://example.com", expected_domain="example.com",
        type=SiteType.laravel, check_interval_seconds=120,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def test_add_site_jobs_creates_expected_jobs(site):
    scheduler.add_site_jobs(site)

    uptime_job = scheduler.scheduler.get_job(f"site:{site.id}:uptime")
    content_job = scheduler.scheduler.get_job(f"site:{site.id}:content")
    ssl_job = scheduler.scheduler.get_job(f"site:{site.id}:ssl_domain")
    deps_job = scheduler.scheduler.get_job(f"site:{site.id}:deps")

    assert uptime_job is not None
    assert isinstance(uptime_job.trigger, IntervalTrigger)
    assert uptime_job.trigger.interval.total_seconds() == 120

    assert content_job is not None
    assert ssl_job is not None
    assert isinstance(ssl_job.trigger, CronTrigger)
    assert deps_job is not None
    # laravel sites get a "deps" job, not "wp"
    assert scheduler.scheduler.get_job(f"site:{site.id}:wp") is None


def test_reload_site_picks_up_interval_change(db, site):
    scheduler.add_site_jobs(site)
    original_job = scheduler.scheduler.get_job(f"site:{site.id}:uptime")
    assert original_job.trigger.interval.total_seconds() == 120

    site.check_interval_seconds = 60
    db.commit()

    scheduler.reload_site(db, site.id)

    updated_job = scheduler.scheduler.get_job(f"site:{site.id}:uptime")
    assert updated_job.trigger.interval.total_seconds() == 60


def test_reload_site_removes_jobs_when_paused(db, site):
    scheduler.add_site_jobs(site)
    assert scheduler.scheduler.get_job(f"site:{site.id}:uptime") is not None

    site.active = False
    db.commit()
    scheduler.reload_site(db, site.id)

    assert scheduler.scheduler.get_job(f"site:{site.id}:uptime") is None
    assert scheduler.scheduler.get_job(f"site:{site.id}:content") is None


def test_remove_site_jobs_clears_everything(site):
    scheduler.add_site_jobs(site)
    assert len(scheduler.scheduler.get_jobs()) > 0

    scheduler.remove_site_jobs(site.id)

    assert scheduler.scheduler.get_jobs() == []


def test_health_check_is_scheduled_on_the_site_interval(site):
    # Regression: "health" was registered as a checker but never added to
    # either INTERVAL_CHECK_TYPES or DAILY_CHECK_TYPES, so it only ever ran
    # via manual check-now or the startup sweep, never on a recurring schedule.
    scheduler.add_site_jobs(site)

    health_job = scheduler.scheduler.get_job(f"site:{site.id}:health")
    assert health_job is not None
    assert isinstance(health_job.trigger, IntervalTrigger)
    assert health_job.trigger.interval.total_seconds() == 120


def test_other_site_type_gets_health_and_deps_jobs_not_wp(db):
    site = Site(
        name="Custom Site",
        url="https://custom.example.com",
        expected_domain="custom.example.com",
        type=SiteType.other,
    )
    db.add(site)
    db.commit()
    db.refresh(site)

    scheduler.add_site_jobs(site)

    assert scheduler.scheduler.get_job(f"site:{site.id}:health") is not None
    assert scheduler.scheduler.get_job(f"site:{site.id}:deps") is not None
    assert scheduler.scheduler.get_job(f"site:{site.id}:wp") is None


def test_wordpress_site_gets_wp_job_not_deps(db):
    site = Site(
        name="WP Site", url="https://wp.example.com", expected_domain="wp.example.com",
        type=SiteType.wordpress,
    )
    db.add(site)
    db.commit()
    db.refresh(site)

    scheduler.add_site_jobs(site)

    assert scheduler.scheduler.get_job(f"site:{site.id}:wp") is not None
    assert scheduler.scheduler.get_job(f"site:{site.id}:deps") is None


def test_basic_monitoring_mode_only_gets_uptime_and_ssl_jobs(db):
    site = Site(
        name="Lightweight",
        url="https://example.com",
        expected_domain="example.com",
        type=SiteType.wordpress,
        monitoring_mode=MonitoringMode.basic,
    )
    db.add(site)
    db.commit()
    db.refresh(site)

    scheduler.add_site_jobs(site)

    assert scheduler.scheduler.get_job(f"site:{site.id}:uptime") is not None
    assert scheduler.scheduler.get_job(f"site:{site.id}:ssl_domain") is not None
    # everything else -- content, wp, blacklist -- must not be scheduled
    assert scheduler.scheduler.get_job(f"site:{site.id}:content") is None
    assert scheduler.scheduler.get_job(f"site:{site.id}:wp") is None
    assert scheduler.scheduler.get_job(f"site:{site.id}:blacklist") is None
