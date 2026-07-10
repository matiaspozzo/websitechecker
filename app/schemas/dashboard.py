from datetime import datetime

from pydantic import BaseModel

from app.models.site import MonitoringMode, SiteType


class SparklinePoint(BaseModel):
    timestamp: datetime
    latency_ms: int | None
    success: bool


class SiteDashboardEntry(BaseModel):
    id: int
    name: str
    url: str
    type: SiteType
    monitoring_mode: MonitoringMode
    active: bool
    status: str  # "up" | "down" | "paused" | "unknown"
    uptime_24h_pct: float | None
    uptime_7d_pct: float | None
    avg_latency_ms: float | None
    sparkline: list[SparklinePoint]
    next_ssl_expiry: datetime | None
    ssl_valid: bool | None
    ssl_error: str | None
    next_domain_expiry: datetime | None
    vulnerable_plugin_count: int
    open_incident_count: int


class DashboardResponse(BaseModel):
    sites: list[SiteDashboardEntry]
