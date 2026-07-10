import logging
import time

import aiohttp

from app.config import settings

logger = logging.getLogger(__name__)

WPSCAN_BASE = "https://wpscan.com/api/v3"
CACHE_TTL_SECONDS = 24 * 3600

# Cache raw WPScan lookups across sites/runs to respect the free tier's 25 req/day limit.
_cache: dict[str, tuple[float, dict | None]] = {}


async def _get_cached_or_fetch(http: aiohttp.ClientSession, cache_key: str, url: str) -> dict | None:
    now = time.monotonic()
    cached = _cache.get(cache_key)
    if cached and now - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    if not settings.wpscan_api_key:
        return None

    headers = {"Authorization": f"Token token={settings.wpscan_api_key}"}
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


async def get_plugin_vulnerabilities(http: aiohttp.ClientSession, slug: str) -> list[dict]:
    data = await _get_cached_or_fetch(http, f"plugin:{slug}", f"{WPSCAN_BASE}/plugins/{slug}")
    if not data or slug not in data:
        return []
    return data[slug].get("vulnerabilities", [])


async def get_theme_vulnerabilities(http: aiohttp.ClientSession, slug: str) -> list[dict]:
    data = await _get_cached_or_fetch(http, f"theme:{slug}", f"{WPSCAN_BASE}/themes/{slug}")
    if not data or slug not in data:
        return []
    return data[slug].get("vulnerabilities", [])


async def get_core_vulnerabilities(http: aiohttp.ClientSession, version: str) -> list[dict]:
    data = await _get_cached_or_fetch(http, f"core:{version}", f"{WPSCAN_BASE}/wordpresses/{version}")
    if not data or version not in data:
        return []
    return data[version].get("vulnerabilities", [])
