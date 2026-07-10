import asyncio
import logging
import socket
import ssl
from datetime import datetime, timezone
from urllib.parse import urlparse

import aiohttp
import whois
from cryptography import x509
from sqlalchemy.orm import Session

from app import incident_manager
from app.checks.base import CheckOutcome
from app.checks.registry import register
from app.models.config import GlobalConfig
from app.models.incident import CheckType, Severity
from app.models.site import Site
from app.models.ssl_domain_status import SslDomainStatus

logger = logging.getLogger(__name__)


def _fetch_peer_cert_expiry(hostname: str, port: int, timeout: float) -> datetime | None:
    """Read the certificate's real notAfter date regardless of whether it would
    pass validation -- an unverified handshake still lets us see an expired or
    self-signed cert's actual expiry, instead of only knowing "invalid"."""
    context = ssl._create_unverified_context()
    try:
        with socket.create_connection((hostname, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                der = ssock.getpeercert(binary_form=True)
    except (OSError, TimeoutError):
        return None
    if not der:
        return None
    cert = x509.load_der_x509_certificate(der)
    return cert.not_valid_after_utc


def _get_ssl_expiry(hostname: str, port: int = 443, timeout: float = 10) -> tuple[datetime | None, str | None]:
    expiry = _fetch_peer_cert_expiry(hostname, port, timeout)

    context = ssl.create_default_context()
    try:
        with socket.create_connection((hostname, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=hostname):
                pass
        return expiry, None
    except ssl.SSLCertVerificationError as exc:
        return expiry, f"SSL verification error: {exc}"
    except (OSError, TimeoutError) as exc:
        return expiry, f"SSL connection error: {exc}"


def _get_domain_expiry(domain: str) -> tuple[datetime | None, str | None]:
    try:
        record = whois.whois(domain)
        expires = record.expiration_date
        if isinstance(expires, list):
            expires = expires[0] if expires else None
        if expires is None:
            return None, "no expiration_date in WHOIS record"
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return expires, None
    except Exception as exc:  # python-whois raises assorted, undocumented exception types
        return None, f"WHOIS error: {exc}"


def _registrable_domain(hostname: str) -> str:
    parts = hostname.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else hostname


class SslDomainChecker:
    check_type = "ssl_domain"

    async def run(self, site: Site, db: Session, http: aiohttp.ClientSession) -> CheckOutcome:
        loop = asyncio.get_event_loop()
        hostname = urlparse(site.url).hostname or site.expected_domain
        registrable_domain = _registrable_domain(hostname)

        config = db.get(GlobalConfig, 1)
        ssl_thresholds = config.ssl_alert_days_json if config else [14, 7, 3]
        domain_thresholds = config.domain_alert_days_json if config else [30, 14, 7]

        ssl_expiry, ssl_error = await loop.run_in_executor(None, _get_ssl_expiry, hostname)
        domain_expiry, whois_error = await loop.run_in_executor(None, _get_domain_expiry, registrable_domain)

        db.add(
            SslDomainStatus(
                site_id=site.id,
                ssl_expires_at=ssl_expiry,
                ssl_valid=ssl_error is None,
                ssl_error=ssl_error,
                domain_expires_at=domain_expiry,
                whois_error=whois_error,
            )
        )
        db.commit()

        now = datetime.now(timezone.utc)

        if ssl_error:
            expiry_note = f" (cert notAfter: {ssl_expiry.date()})" if ssl_expiry else ""
            await incident_manager.open_incident(
                db,
                site,
                CheckType.ssl,
                Severity.critical,
                cause=f"{site.name} SSL error: {ssl_error}{expiry_note}",
                detail={"error": ssl_error, "expires_at": ssl_expiry.isoformat() if ssl_expiry else None},
            )
        elif ssl_expiry:
            days_remaining = (ssl_expiry - now).days
            await incident_manager.maybe_alert_threshold_crossing(
                db,
                site,
                CheckType.ssl,
                Severity.critical if days_remaining <= 3 else Severity.warning,
                cause=f"{site.name} SSL cert expires in {days_remaining} days ({ssl_expiry.date()})",
                days_remaining=days_remaining,
                thresholds=ssl_thresholds,
                detail={"expires_at": ssl_expiry.isoformat()},
            )

        if whois_error:
            logger.warning("WHOIS lookup failed for %s: %s", registrable_domain, whois_error)
        elif domain_expiry:
            days_remaining = (domain_expiry - now).days
            await incident_manager.maybe_alert_threshold_crossing(
                db,
                site,
                CheckType.domain,
                Severity.critical if days_remaining <= 7 else Severity.warning,
                cause=f"{site.name} domain expires in {days_remaining} days ({domain_expiry.date()})",
                days_remaining=days_remaining,
                thresholds=domain_thresholds,
                detail={"expires_at": domain_expiry.isoformat()},
            )

        return CheckOutcome(success=ssl_error is None and whois_error is None, check_type=self.check_type)


register(SslDomainChecker())
