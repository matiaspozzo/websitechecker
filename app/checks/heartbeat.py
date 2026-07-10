import logging
import time
from pathlib import Path

import aiohttp

from app.config import settings
from app.database import SessionLocal
from app.models.config import GlobalConfig

logger = logging.getLogger(__name__)

LAST_ALIVE_FILE = Path(settings.log_dir).parent / "last_alive.txt"

# Heartbeat runs every 5 min; allow some slack before treating a gap as real downtime.
STARTUP_DOWNTIME_THRESHOLD_SECONDS = 600


def _healthchecks_url(db) -> str | None:
    config = db.get(GlobalConfig, 1)
    return (config.healthchecks_url if config else None) or settings.healthchecks_url


def _touch_last_alive() -> None:
    LAST_ALIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
    LAST_ALIVE_FILE.write_text(str(time.time()))


async def send_heartbeat() -> None:
    db = SessionLocal()
    try:
        url = _healthchecks_url(db)
    finally:
        db.close()

    _touch_last_alive()

    if not url:
        logger.debug("Healthchecks URL not configured; skipping heartbeat ping")
        return

    try:
        async with aiohttp.ClientSession(headers={"User-Agent": "SiteWatch/1.0"}) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    logger.warning("Heartbeat ping returned HTTP %s", resp.status)
    except aiohttp.ClientError as exc:
        logger.warning("Heartbeat ping failed: %s", exc)


async def check_startup_downtime() -> None:
    """Compare the last-alive marker on disk to now. If the gap is bigger than the
    heartbeat interval allows for, SiteWatch itself was down -- notify Telegram with
    how long, and immediately run a full check of every active site."""
    if not LAST_ALIVE_FILE.exists():
        _touch_last_alive()
        return

    try:
        last_alive = float(LAST_ALIVE_FILE.read_text().strip())
    except (ValueError, OSError):
        _touch_last_alive()
        return

    gap = time.time() - last_alive
    _touch_last_alive()

    if gap <= STARTUP_DOWNTIME_THRESHOLD_SECONDS:
        return

    from app.notifiers.telegram import send_startup_downtime_notice

    await send_startup_downtime_notice(gap)
    await _run_check_now_all_sites()


async def _run_check_now_all_sites() -> None:
    from app.checks.runner import run_all_checks_for_site
    from app.models.site import Site

    db = SessionLocal()
    try:
        sites = db.query(Site).filter(Site.active.is_(True)).all()
    finally:
        db.close()

    for site in sites:
        db_site = SessionLocal()
        try:
            await run_all_checks_for_site(site, db_site)
        finally:
            db_site.close()
