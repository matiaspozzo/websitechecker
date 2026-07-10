from pydantic import BaseModel, ConfigDict

from app.models.suspicious_pattern import PatternSeverity


class GlobalConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_chat_id: str | None
    digest_hour: int
    digest_timezone: str
    ssl_alert_days_json: list[int]
    domain_alert_days_json: list[int]
    panel_base_url: str
    wpscan_api_key: str | None
    gsb_api_key: str | None
    vt_api_key: str | None
    healthchecks_url: str | None
    wpscan_daily_limit: int
    wpscan_requests_today: int
    wpscan_requests_date: str | None


class GlobalConfigUpdate(BaseModel):
    telegram_chat_id: str | None = None
    digest_hour: int | None = None
    digest_timezone: str | None = None
    ssl_alert_days_json: list[int] | None = None
    domain_alert_days_json: list[int] | None = None
    panel_base_url: str | None = None
    wpscan_api_key: str | None = None
    gsb_api_key: str | None = None
    vt_api_key: str | None = None
    healthchecks_url: str | None = None
    wpscan_daily_limit: int | None = None


class SuspiciousPatternBase(BaseModel):
    pattern: str
    is_regex: bool = False
    description: str | None = None
    enabled: bool = True
    severity: PatternSeverity = PatternSeverity.critical


class SuspiciousPatternCreate(SuspiciousPatternBase):
    pass


class SuspiciousPatternUpdate(BaseModel):
    pattern: str | None = None
    is_regex: bool | None = None
    description: str | None = None
    enabled: bool | None = None
    severity: PatternSeverity | None = None


class SuspiciousPatternOut(SuspiciousPatternBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class TrustedDomainBase(BaseModel):
    domain: str
    description: str | None = None
    enabled: bool = True


class TrustedDomainCreate(TrustedDomainBase):
    pass


class TrustedDomainUpdate(BaseModel):
    domain: str | None = None
    description: str | None = None
    enabled: bool | None = None


class TrustedDomainOut(TrustedDomainBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
