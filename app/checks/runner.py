import logging

import aiohttp
from sqlalchemy.orm import Session

from app.checks.registry import get_checker, load_all_checkers
from app.models.check_result import CheckResult
from app.models.incident import CheckType
from app.models.site import Site

logger = logging.getLogger(__name__)

_http_session: aiohttp.ClientSession | None = None

USER_AGENT = "SiteWatch/1.0"


def set_http_session(session: aiohttp.ClientSession | None) -> None:
    global _http_session
    _http_session = session


async def get_http_session() -> aiohttp.ClientSession:
    global _http_session
    if _http_session is None or _http_session.closed:
        _http_session = aiohttp.ClientSession(
            headers={"User-Agent": USER_AGENT},
            timeout=aiohttp.ClientTimeout(total=10),
        )
    return _http_session


async def run_all_checks_for_site(site: Site, db: Session) -> None:
    """Run every check applicable to this site (its type and monitoring mode),
    one after another. A failing check must not prevent the others from running."""
    from app.checks.registry import applicable_check_types

    load_all_checkers()
    for check_type in applicable_check_types(site):
        try:
            await run_check_for_site(site, check_type, db)
        except Exception:
            logger.exception("Check %s failed for site %s", check_type, site.id)


async def run_check_for_site(site: Site, check_type: str, db: Session) -> None:
    """Dispatch a single check for a single site. Checkers are responsible for
    opening/closing their own incidents via app.incident_manager; this function
    just runs the checker and logs the raw result to the CheckResult time series."""
    load_all_checkers()
    checker = get_checker(check_type)
    http = await get_http_session()

    outcome = await checker.run(site, db, http)

    if outcome.check_type in {ct.value for ct in CheckType}:
        db.add(
            CheckResult(
                site_id=site.id,
                check_type=CheckType(outcome.check_type),
                success=outcome.success,
                latency_ms=outcome.latency_ms,
                status_code=outcome.status_code,
                error_message=outcome.error_message,
            )
        )
        db.commit()
