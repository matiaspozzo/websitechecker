from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models.check_result import CheckResult
from app.models.incident import CheckType, Incident
from app.models.site import Site, SiteType
from app.models.ssl_domain_status import SslDomainStatus
from app.models.wp_snapshot import WpSnapshot
from app.schemas.dashboard import DashboardResponse, SiteDashboardEntry, SparklinePoint

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=DashboardResponse)
def get_dashboard(db: Session = Depends(get_db)) -> DashboardResponse:
    sites = db.query(Site).order_by(Site.name).all()
    now = datetime.now(timezone.utc)
    since_24h = now - timedelta(hours=24)
    since_7d = now - timedelta(days=7)

    entries = []
    for site in sites:
        results_7d = (
            db.query(CheckResult)
            .filter(
                CheckResult.site_id == site.id,
                CheckResult.check_type == CheckType.uptime,
                CheckResult.timestamp >= since_7d,
            )
            .order_by(CheckResult.timestamp)
            .all()
        )
        results_24h = [r for r in results_7d if r.timestamp >= since_24h]

        uptime_24h = 100.0 * sum(1 for r in results_24h if r.success) / len(results_24h) if results_24h else None
        uptime_7d = 100.0 * sum(1 for r in results_7d if r.success) / len(results_7d) if results_7d else None
        latencies = [r.latency_ms for r in results_7d if r.latency_ms is not None]
        avg_latency = sum(latencies) / len(latencies) if latencies else None

        sparkline = [
            SparklinePoint(timestamp=r.timestamp, latency_ms=r.latency_ms, success=r.success)
            for r in results_7d[-30:]
        ]

        if not site.active:
            current_status = "paused"
        elif results_7d:
            current_status = "up" if results_7d[-1].success else "down"
        else:
            current_status = "unknown"

        ssl_status = (
            db.query(SslDomainStatus)
            .filter(SslDomainStatus.site_id == site.id)
            .order_by(SslDomainStatus.timestamp.desc())
            .first()
        )

        open_wp_cve = (
            db.query(Incident)
            .filter(
                Incident.site_id == site.id,
                Incident.check_type == CheckType.wp_cve,
                Incident.closed_at.is_(None),
            )
            .count()
        )
        open_incidents = (
            db.query(Incident).filter(Incident.site_id == site.id, Incident.closed_at.is_(None)).count()
        )

        outdated_plugin_count = 0
        core_update_available = None
        if site.type == SiteType.wordpress:
            wp_snapshot = (
                db.query(WpSnapshot)
                .filter(WpSnapshot.site_id == site.id)
                .order_by(WpSnapshot.timestamp.desc())
                .first()
            )
            if wp_snapshot:
                outdated_plugin_count = sum(
                    1
                    for plugin in wp_snapshot.plugins_json
                    if plugin.get("available") and plugin.get("available") != plugin.get("installed")
                )
                core_update_available = wp_snapshot.core_update_available

        entries.append(
            SiteDashboardEntry(
                id=site.id,
                name=site.name,
                client_name=site.client_name,
                url=site.url,
                type=site.type,
                monitoring_mode=site.monitoring_mode,
                active=site.active,
                status=current_status,
                uptime_24h_pct=uptime_24h,
                uptime_7d_pct=uptime_7d,
                avg_latency_ms=avg_latency,
                sparkline=sparkline,
                next_ssl_expiry=ssl_status.ssl_expires_at if ssl_status else None,
                ssl_valid=ssl_status.ssl_valid if ssl_status else None,
                ssl_error=ssl_status.ssl_error if ssl_status else None,
                next_domain_expiry=ssl_status.domain_expires_at if ssl_status else None,
                vulnerable_plugin_count=open_wp_cve,
                outdated_plugin_count=outdated_plugin_count,
                core_update_available=core_update_available,
                open_incident_count=open_incidents,
            )
        )

    return DashboardResponse(sites=entries)
