import logging
import time
from datetime import date

import aiohttp
from sqlalchemy.orm import Session

from app.config import settings
from app.models.config import GlobalConfig

logger = logging.getLogger(__name__)

WPSCAN_BASE = "https://wpscan.com/api/v3"
CACHE_TTL_SECONDS = 24 * 3600

# Cache raw WPScan lookups across sites/runs -- shared plugin slugs across
# sites (e.g. "elementor") only cost one request per day, not one per site.
_cache: dict[str, tuple[float, dict | None]] = {}


def _reserve_budget(config: GlobalConfig, db: Session) -> bool:
    """Check-and-increment the persisted daily WPScan request counter in one
    synchronous DB round-trip (no `await` in between, so this is atomic within
    asyncio's single-threaded event loop even if multiple sites' checks are
    interleaved). Returns False once today's budget is used up; skipped
    lookups aren't cached, so they're retried for free on a later day."""
    today = date.today().isoformat()
    if config.wpscan_requests_date != today:
        config.wpscan_requests_date = today
        config.wpscan_requests_today = 0

    if config.wpscan_requests_today >= config.wpscan_daily_limit:
        db.commit()
        return False

    config.wpscan_requests_today += 1
    db.commit()
    return True


async def _get_cached_or_fetch(db: Session, http: aiohttp.ClientSession, cache_key: str, url: str) -> dict | None:
    now = time.monotonic()
    cached = _cache.get(cache_key)
    if cached and now - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    config = db.get(GlobalConfig, 1)
    api_key = (config.wpscan_api_key if config else None) or settings.wpscan_api_key
    if not api_key:
        return None

    if config is not None and not _reserve_budget(config, db):
        logger.warning(
            "WPScan daily request budget exhausted; deferring lookup for %s to a later day", cache_key
        )
        return None

    headers = {"Authorization": f"Token token={api_key}"}
    try:
        async with http.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                _cache[cache_key] = (now, None)
                return None
            data = await resp.json()
    except aiohttp.ClientError as exc:
        logger.warning("WPScan request failed for %s: %s", url, exc)
        return None

    _cache[cache_key] = (now, data)
    return data


async def get_plugin_vulnerabilities(db: Session, http: aiohttp.ClientSession, slug: str) -> list[dict]:
    data = await _get_cached_or_fetch(db, http, f"plugin:{slug}", f"{WPSCAN_BASE}/plugins/{slug}")
    if not data or slug not in data:
        return []
    return data[slug].get("vulnerabilities", [])


async def get_theme_vulnerabilities(db: Session, http: aiohttp.ClientSession, slug: str) -> list[dict]:
    data = await _get_cached_or_fetch(db, http, f"theme:{slug}", f"{WPSCAN_BASE}/themes/{slug}")
    if not data or slug not in data:
        return []
    return data[slug].get("vulnerabilities", [])


async def get_core_vulnerabilities(db: Session, http: aiohttp.ClientSession, version: str) -> list[dict]:
    data = await _get_cached_or_fetch(db, http, f"core:{version}", f"{WPSCAN_BASE}/wordpresses/{version}")
    if not data or version not in data:
        return []
    return data[version].get("vulnerabilities", [])
