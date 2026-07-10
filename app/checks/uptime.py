import logging

import aiohttp
from sqlalchemy.orm import Session

from app import incident_manager
from app.checks.base import CheckOutcome
from app.checks.fetch import fetch_with_retry
from app.checks.registry import register
from app.models.incident import CheckType, Severity
from app.models.site import Site

logger = logging.getLogger(__name__)


class UptimeChecker:
    check_type = "uptime"

    async def run(self, site: Site, db: Session, http: aiohttp.ClientSession) -> CheckOutcome:
        result = await fetch_with_retry(http, site.url)

        if result.ok:
            await incident_manager.close_incident(db, site, CheckType.uptime)
            return CheckOutcome(
                success=True,
                check_type=self.check_type,
                latency_ms=result.latency_ms,
                status_code=result.status,
            )

        cause = result.error or f"HTTP {result.status}"
        await incident_manager.open_incident(
            db,
            site,
            CheckType.uptime,
            Severity.critical,
            cause=f"{site.name} is down: {cause}",
            detail={"error": result.error, "status": result.status},
        )
        return CheckOutcome(
            success=False,
            check_type=self.check_type,
            latency_ms=result.latency_ms,
            status_code=result.status,
            error_message=result.error,
            severity="critical",
            cause=cause,
        )


register(UptimeChecker())
