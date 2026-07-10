import pytest
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app import scheduler
from app.models.site import Site, SiteType


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
