import enum
from datetime import datetime

from sqlalchemy import Boolean, Enum, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.types import UTCDateTime


class SiteType(str, enum.Enum):
    wordpress = "wordpress"
    laravel = "laravel"
    nextjs = "nextjs"


class MonitoringMode(str, enum.Enum):
    full = "full"  # all checks applicable to the site's type
    basic = "basic"  # uptime + SSL/domain expiry only, nothing else


class Site(Base):
    __tablename__ = "sites"
    __table_args__ = (Index("ix_sites_client_name", "client_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str] = mapped_column(String(1024))
    expected_domain: Mapped[str] = mapped_column(String(255))
    type: Mapped[SiteType] = mapped_column(Enum(SiteType))
    monitoring_mode: Mapped[MonitoringMode] = mapped_column(
        Enum(MonitoringMode), default=MonitoringMode.full, server_default=MonitoringMode.full.value
    )
    check_interval_seconds: Mapped[int] = mapped_column(Integer, default=300)
    expected_keyword: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    # WordPress-only
    mu_plugin_token: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Laravel/Next.js
    health_endpoint_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    ssh_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ssh_user: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ssh_key_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    ssh_project_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    audit_fetch_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    audit_fetch_token: Mapped[str | None] = mapped_column(String(255), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, server_default=func.now(), onupdate=func.now())

    incidents: Mapped[list["Incident"]] = relationship(
        back_populates="site", cascade="all, delete-orphan"
    )
    check_results: Mapped[list["CheckResult"]] = relationship(
        back_populates="site", cascade="all, delete-orphan"
    )
    wp_snapshots: Mapped[list["WpSnapshot"]] = relationship(
        back_populates="site", cascade="all, delete-orphan"
    )
    dependency_audits: Mapped[list["DependencyAudit"]] = relationship(
        back_populates="site", cascade="all, delete-orphan"
    )
    ssl_domain_statuses: Mapped[list["SslDomainStatus"]] = relationship(
        back_populates="site", cascade="all, delete-orphan"
    )
    blacklist_statuses: Mapped[list["BlacklistStatus"]] = relationship(
        back_populates="site", cascade="all, delete-orphan"
    )
    silences: Mapped[list["Silence"]] = relationship(
        back_populates="site", cascade="all, delete-orphan"
    )
