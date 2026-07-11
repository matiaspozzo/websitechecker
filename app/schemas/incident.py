from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.incident import CheckType, Severity


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    check_type: CheckType
    severity: Severity
    opened_at: datetime
    closed_at: datetime | None
    acknowledged_at: datetime | None
    cause: str
    detail_json: dict
