from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.site import MonitoringMode, SiteType

# Fields where leading/trailing whitespace can silently break something rather
# than just look untidy: a stray trailing space in a URL breaks DNS resolution
# entirely (confirmed in the wild -- a site pasted with a trailing space
# resolved to nothing and got reported as "down" with no useful error), and a
# stray space in client_name would silently fork the dashboard's client filter
# into two buckets for what's supposed to be the same client.
_TRIMMED_FIELDS = (
    "name",
    "client_name",
    "url",
    "expected_keyword",
    "mu_plugin_token",
    "health_endpoint_url",
    "ssh_host",
    "ssh_user",
    "ssh_key_path",
    "ssh_project_path",
    "audit_fetch_url",
    "audit_fetch_token",
)


class _TrimStringsMixin:
    @field_validator(*_TRIMMED_FIELDS, mode="before", check_fields=False)
    @classmethod
    def _strip_whitespace(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class SiteBase(_TrimStringsMixin, BaseModel):
    name: str
    client_name: str | None = None
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


class SiteUpdate(_TrimStringsMixin, BaseModel):
    name: str | None = None
    client_name: str | None = None
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
