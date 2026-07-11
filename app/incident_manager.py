import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.incident import CheckType, Incident, Severity
from app.models.silence import Silence
from app.models.site import Site

logger = logging.getLogger(__name__)


def _is_silenced(db: Session, site_id: int) -> bool:
    now = datetime.now(timezone.utc)
    return (
        db.query(Silence)
        .filter(Silence.site_id == site_id, Silence.until > now)
        .first()
        is not None
    )


def get_open_incident(db: Session, site_id: int, check_type: CheckType) -> Incident | None:
    return (
        db.query(Incident)
        .filter(
            Incident.site_id == site_id,
            Incident.check_type == check_type,
            Incident.closed_at.is_(None),
        )
        .first()
    )


async def open_incident(
    db: Session,
    site: Site,
    check_type: CheckType,
    severity: Severity,
    cause: str,
    detail: dict | None = None,
) -> Incident:
    """Open a new incident, or refresh an already-open one of the same type without re-notifying."""
    from app.notifiers.telegram import send_incident_open

    detail = detail or {}
    existing = get_open_incident(db, site.id, check_type)
    if existing is not None:
        # An acknowledgment ("I know, I've mitigated this") only covers the specific
        # situation it was made against. If the cause text actually changed -- a
        # different plugin/CVE now driving the same shared incident type, or a new
        # detail on the same one -- that's new information the ack didn't cover, so
        # it needs fresh attention rather than staying silently suppressed.
        if existing.acknowledged_at is not None and existing.cause != cause:
            existing.acknowledged_at = None
        existing.cause = cause
        existing.detail_json = {**existing.detail_json, **detail}
        db.commit()
        return existing

    incident = Incident(
        site_id=site.id,
        check_type=check_type,
        severity=severity,
        cause=cause,
        detail_json=detail,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    if _is_silenced(db, site.id):
        logger.info("Incident %s for site %s suppressed (silenced)", check_type.value, site.id)
    else:
        await send_incident_open(incident, site)
        incident.notified_open_at = datetime.now(timezone.utc)
        db.commit()

    return incident


async def close_incident(db: Session, site: Site, check_type: CheckType) -> Incident | None:
    from app.notifiers.telegram import send_incident_close

    incident = get_open_incident(db, site.id, check_type)
    if incident is None:
        return None

    incident.closed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(incident)

    if _is_silenced(db, site.id):
        logger.info("Recovery %s for site %s suppressed (silenced)", check_type.value, site.id)
    else:
        await send_incident_close(incident, site)
        incident.notified_close_at = datetime.now(timezone.utc)
        db.commit()

    return incident


async def maybe_alert_threshold_crossing(
    db: Session,
    site: Site,
    check_type: CheckType,
    severity: Severity,
    cause: str,
    days_remaining: int,
    thresholds: list[int],
    detail: dict | None = None,
) -> Incident | None:
    """For expiry-style checks (SSL/domain): open/refresh an incident but only send a new
    Telegram message when crossing to a MORE urgent threshold than last alerted."""
    detail = detail or {}
    crossed = [t for t in sorted(thresholds, reverse=True) if days_remaining <= t]
    if not crossed:
        # Beyond all thresholds (e.g. renewed) -> close any open incident of this type.
        return await close_incident(db, site, check_type)

    most_urgent_crossed = min(crossed)
    existing = get_open_incident(db, site.id, check_type)

    if existing is not None:
        last_alerted = existing.detail_json.get("last_alerted_threshold")
        existing.cause = cause
        existing.detail_json = {**existing.detail_json, **detail, "days_remaining": days_remaining}
        should_notify = last_alerted is None or most_urgent_crossed < last_alerted
        db.commit()
        if should_notify and not _is_silenced(db, site.id):
            from app.notifiers.telegram import send_incident_open

            existing.detail_json = {**existing.detail_json, "last_alerted_threshold": most_urgent_crossed}
            db.commit()
            await send_incident_open(existing, site)
        return existing

    incident = Incident(
        site_id=site.id,
        check_type=check_type,
        severity=severity,
        cause=cause,
        detail_json={**detail, "days_remaining": days_remaining, "last_alerted_threshold": most_urgent_crossed},
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    if not _is_silenced(db, site.id):
        from app.notifiers.telegram import send_incident_open

        await send_incident_open(incident, site)
        incident.notified_open_at = datetime.now(timezone.utc)
        db.commit()

    return incident


def acknowledge_incident(db: Session, incident: Incident) -> Incident:
    """Mark an open incident as acknowledged: e.g. a vulnerable plugin has no fix
    yet and was deactivated as a mitigation instead. Distinct from `Silence`, which
    only mutes Telegram sends for a fixed window -- acknowledging clears the
    incident from dashboard badges immediately and stays in effect indefinitely,
    but the incident itself remains open and visible in incident history until the
    underlying check actually clears it. A later cause change (see `open_incident`)
    auto-clears the ack, since it means something new is going on."""
    incident.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(incident)
    return incident


def unacknowledge_incident(db: Session, incident: Incident) -> Incident:
    incident.acknowledged_at = None
    db.commit()
    db.refresh(incident)
    return incident

    return incident
