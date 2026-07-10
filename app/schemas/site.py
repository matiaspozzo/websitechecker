from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.site import MonitoringMode, SiteType


class SiteBase(BaseModel):
    name: str
    url: str
    type: SiteType
    monitoring_mode: MonitoringMode = MonitoringMode.full
    check_interval_seconds: int = 300
    expected_keyword: str | None = None
    active: bool = True
    mu_plugin_token: str | None = None
    health_endpoint_url: str | None = None
    ssh_host: str | None = None
    ssh_user: str | None = None
    ssh_key_path: str | None = None
    ssh_project_path: str | None = None
    audit_fetch_url: str | None = None
    audit_fetch_token: str | None = None
    notes: str | None = None


class SiteCreate(SiteBase):
    pass


class SiteUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    type: SiteType | None = None
    monitoring_mode: MonitoringMode | None = None
    check_interval_seconds: int | None = None
    expected_keyword: str | None = None
    active: bool | None = None
    mu_plugin_token: str | None = None
    health_endpoint_url: str | None = None
    ssh_host: str | None = None
    ssh_user: str | None = None
    ssh_key_path: str | None = None
    ssh_project_path: str | None = None
    audit_fetch_url: str | None = None
    audit_fetch_token: str | None = None
    notes: str | None = None


class SiteOut(SiteBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    expected_domain: str
    created_at: datetime
    updated_at: datetime


class SilenceRequest(BaseModel):
    hours: float
