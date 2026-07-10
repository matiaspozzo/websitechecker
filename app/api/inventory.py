from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.checks.wordpress import CURRENT_MU_PLUGIN_VERSION
from app.deps import get_current_user, get_db
from app.models.check_result import CheckResult
from app.models.dependency_audit import DependencyAudit
from app.models.incident import CheckType
from app.models.site import Site
from app.models.wp_snapshot import WpSnapshot

router = APIRouter(prefix="/api/sites", tags=["inventory"], dependencies=[Depends(get_current_user)])


def _require_site(site_id: int, db: Session) -> Site:
    site = db.get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return site


@router.get("/{site_id}/wp-inventory")
def get_wp_inventory(site_id: int, db: Session = Depends(get_db)) -> dict:
    site = _require_site(site_id, db)
    snapshot = (
        db.query(WpSnapshot)
        .filter(WpSnapshot.site_id == site_id)
        .order_by(WpSnapshot.timestamp.desc())
        .first()
    )
    if snapshot is None:
        return {"snapshot": None}
    return {
        "snapshot": {
            "timestamp": snapshot.timestamp,
            "mu_plugin_version": snapshot.mu_plugin_version,
            "mu_plugin_outdated": bool(site.mu_plugin_token) and snapshot.mu_plugin_version != CURRENT_MU_PLUGIN_VERSION,
            "core_version": snapshot.core_version,
            "core_update_available": snapshot.core_update_available,
            "php_version": snapshot.php_version,
            "plugins": snapshot.plugins_json,
            "themes": snapshot.themes_json,
            "admin_usernames": snapshot.admin_usernames_json,
        }
    }


@router.get("/{site_id}/dependency-audits")
def get_dependency_audits(site_id: int, limit: int = 10, db: Session = Depends(get_db)) -> list[dict]:
    _require_site(site_id, db)
    audits = (
        db.query(DependencyAudit)
        .filter(DependencyAudit.site_id == site_id)
        .order_by(DependencyAudit.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": a.id,
            "timestamp": a.timestamp,
            "tool": a.tool,
            "high_critical_count": a.high_critical_count,
            "summary": a.summary,
        }
        for a in audits
    ]


@router.get("/{site_id}/latency")
def get_latency_series(
    site_id: int, range: str = Query(default="7d", pattern="^(7d|30d)$"), db: Session = Depends(get_db)
) -> list[dict]:
    _require_site(site_id, db)
    days = 30 if range == "30d" else 7
    since = datetime.now(timezone.utc) - timedelta(days=days)
    results = (
        db.query(CheckResult)
        .filter(
            CheckResult.site_id == site_id,
            CheckResult.check_type == CheckType.uptime,
            CheckResult.timestamp >= since,
        )
        .order_by(CheckResult.timestamp)
        .all()
    )
    return [
        {"timestamp": r.timestamp, "latency_ms": r.latency_ms, "success": r.success}
        for r in results
    ]
