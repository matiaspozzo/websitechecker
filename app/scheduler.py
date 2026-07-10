import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.config import GlobalConfig
from app.models.site import Site, SiteType

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone=settings.tz)

# Checks that run on the site's own configured interval (fast, frequent).
INTERVAL_CHECK_TYPES = ["uptime", "content"]

# Checks that run once/day, staggered per-site to avoid a thundering herd.
DAILY_CHECK_TYPES = {
    "ssl_domain": 2,  # base hour
    "wp": 3,
    "deps": 4,
    "blacklist": 5,
}

HEARTBEAT_JOB_ID = "heartbeat"
DIGEST_JOB_ID = "digest"


def _job_id(site_id: int, check_type: str) -> str:
    return f"site:{site_id}:{check_type}"


def _daily_check_types_for_site(site: Site) -> list[str]:
    types = ["ssl_domain", "blacklist"]
    if site.type == SiteType.wordpress:
        types.append("wp")
    else:
        types.append("deps")
    return types


async def _run_job(site_id: int, check_type: str) -> None:
    """Entry point scheduled for every site+check job. Never raises -- a failing
    site/check must not prevent other jobs from running."""
    from app.checks.runner import run_check_for_site

    db = SessionLocal()
    try:
        site = db.get(Site, site_id)
        if site is None or not site.active:
            return
        await run_check_for_site(site, check_type, db)
    except Exception:
        logger.exception("Check %s failed for site %s", check_type, site_id)
    finally:
        db.close()


async def _run_digest() -> None:
    from app.notifiers.telegram import send_digest

    try:
        await send_digest()
    except Exception:
        logger.exception("Failed to send daily digest")


async def _run_heartbeat() -> None:
    from app.checks.heartbeat import send_heartbeat

    try:
        await send_heartbeat()
    except Exception:
        logger.exception("Failed to send heartbeat")


def add_site_jobs(site: Site) -> None:
    if not site.active:
        return

    for check_type in INTERVAL_CHECK_TYPES:
        scheduler.add_job(
            _run_job,
            trigger=IntervalTrigger(seconds=site.check_interval_seconds),
            args=[site.id, check_type],
            id=_job_id(site.id, check_type),
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

    stagger_minute = site.id % 60
    for check_type in _daily_check_types_for_site(site):
        base_hour = DAILY_CHECK_TYPES[check_type]
        scheduler.add_job(
            _run_job,
            trigger=CronTrigger(hour=base_hour, minute=stagger_minute),
            args=[site.id, check_type],
            id=_job_id(site.id, check_type),
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )


def remove_site_jobs(site_id: int) -> None:
    for job in scheduler.get_jobs():
        if job.id.startswith(f"site:{site_id}:"):
            scheduler.remove_job(job.id)


def reload_site(db: Session, site_id: int) -> None:
    remove_site_jobs(site_id)
    site = db.get(Site, site_id)
    if site is not None:
        add_site_jobs(site)


def reload_digest_job(db: Session) -> None:
    config = db.get(GlobalConfig, 1)
    hour = config.digest_hour if config else 9
    scheduler.add_job(
        _run_digest,
        trigger=CronTrigger(hour=hour, minute=0),
        id=DIGEST_JOB_ID,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )


def sync_all_sites(db: Session) -> None:
    for job in scheduler.get_jobs():
        if job.id.startswith("site:"):
            scheduler.remove_job(job.id)

    for site in db.query(Site).filter(Site.active.is_(True)).all():
        add_site_jobs(site)

    reload_digest_job(db)

    scheduler.add_job(
        _run_heartbeat,
        trigger=IntervalTrigger(minutes=5),
        id=HEARTBEAT_JOB_ID,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )


def start() -> None:
    if not scheduler.running:
        scheduler.start()


def shutdown() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
