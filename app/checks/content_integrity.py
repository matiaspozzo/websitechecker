import logging
import re
from urllib.parse import urlparse

import aiohttp
from sqlalchemy.orm import Session

from app import incident_manager
from app.checks.base import CheckOutcome
from app.checks.fetch import fetch_with_retry
from app.checks.registry import register
from app.models.incident import CheckType, Severity
from app.models.site import Site
from app.models.suspicious_pattern import SuspiciousPattern
from app.models.trusted_domain import TrustedDomain

logger = logging.getLogger(__name__)

IFRAME_RE = re.compile(r'<iframe[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
META_REFRESH_RE = re.compile(
    r'<meta[^>]+http-equiv=["\']refresh["\'][^>]*content=["\'][^"\']*url=([^"\';]+)', re.IGNORECASE
)


def _is_trusted_domain(domain: str, expected_domain: str, trusted_domains: list[str]) -> bool:
    if expected_domain in domain:
        return True
    return any(domain == d or domain.endswith(f".{d}") for d in trusted_domains)


class ContentIntegrityChecker:
    check_type = "content"

    async def run(self, site: Site, db: Session, http: aiohttp.ClientSession) -> CheckOutcome:
        result = await fetch_with_retry(http, site.url)

        if not result.ok or result.body is None:
            # The uptime checker already reports this failure; nothing content-specific to say.
            return CheckOutcome(success=True, check_type=self.check_type)

        issues: list[str] = []

        if site.expected_keyword and site.expected_keyword not in result.body:
            issues.append(f"expected keyword '{site.expected_keyword}' not found")

        patterns = db.query(SuspiciousPattern).filter(SuspiciousPattern.enabled.is_(True)).all()
        for pattern in patterns:
            matched = (
                re.search(pattern.pattern, result.body)
                if pattern.is_regex
                else pattern.pattern in result.body
            )
            if matched:
                issues.append(f"suspicious pattern matched: {pattern.description or pattern.pattern}")

        expected_domain = site.expected_domain
        trusted_domains = [
            d.domain for d in db.query(TrustedDomain).filter(TrustedDomain.enabled.is_(True)).all()
        ]

        for match in IFRAME_RE.finditer(result.body):
            domain = urlparse(match.group(1)).netloc
            if domain and not _is_trusted_domain(domain, expected_domain, trusted_domains):
                issues.append(f"iframe to unknown domain: {domain}")

        for match in META_REFRESH_RE.finditer(result.body):
            domain = urlparse(match.group(1).strip()).netloc
            if domain and not _is_trusted_domain(domain, expected_domain, trusted_domains):
                issues.append(f"external meta-refresh to {domain}")

        content_ok = not issues
        if content_ok:
            await incident_manager.close_incident(db, site, CheckType.content)
        else:
            await incident_manager.open_incident(
                db,
                site,
                CheckType.content,
                Severity.critical,
                cause=f"{site.name} content integrity issue: " + "; ".join(issues),
                detail={"issues": issues},
            )

        redirect_ok = True
        final_domain = None
        if result.final_url:
            final_domain = urlparse(result.final_url).netloc
            redirect_ok = not final_domain or expected_domain in final_domain

        if redirect_ok:
            await incident_manager.close_incident(db, site, CheckType.redirect)
        else:
            await incident_manager.open_incident(
                db,
                site,
                CheckType.redirect,
                Severity.critical,
                cause=f"{site.name} redirected to unexpected domain: {final_domain}",
                detail={"final_url": result.final_url},
            )

        return CheckOutcome(
            success=content_ok and redirect_ok,
            check_type=self.check_type,
            latency_ms=result.latency_ms,
            status_code=result.status,
        )


register(ContentIntegrityChecker())
