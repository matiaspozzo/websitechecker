from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import incident_manager
from app.deps import get_current_user, get_db
from app.models.incident import CheckType, Incident
from app.schemas.incident import IncidentOut

router = APIRouter(prefix="/api/incidents", tags=["incidents"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[IncidentOut])
def list_incidents(
    site_id: int | None = None,
    check_type: CheckType | None = None,
    open: bool | None = Query(default=None),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
) -> list[Incident]:
    q = db.query(Incident)
    if site_id is not None:
        q = q.filter(Incident.site_id == site_id)
    if check_type is not None:
        q = q.filter(Incident.check_type == check_type)
    if open is True:
        q = q.filter(Incident.closed_at.is_(None))
    elif open is False:
        q = q.filter(Incident.closed_at.is_not(None))
    if date_from is not None:
        q = q.filter(Incident.opened_at >= date_from)
    if date_to is not None:
        q = q.filter(Incident.opened_at <= date_to)
    return q.order_by(Incident.opened_at.desc()).limit(500).all()


def _get_incident_or_404(incident_id: int, db: Session) -> Incident:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.post("/{incident_id}/acknowledge", response_model=IncidentOut)
def acknowledge_incident(incident_id: int, db: Session = Depends(get_db)) -> Incident:
    incident = _get_incident_or_404(incident_id, db)
    if incident.closed_at is not None:
        raise HTTPException(status_code=400, detail="Cannot acknowledge a closed incident")
    return incident_manager.acknowledge_incident(db, incident)


@router.post("/{incident_id}/unacknowledge", response_model=IncidentOut)
def unacknowledge_incident(incident_id: int, db: Session = Depends(get_db)) -> Incident:
    incident = _get_incident_or_404(incident_id, db)
    return incident_manager.unacknowledge_incident(db, incident)
