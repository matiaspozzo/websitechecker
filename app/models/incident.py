import enum
from datetime import datetime

from sqlalchemy import JSON, Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.types import UTCDateTime


class CheckType(str, enum.Enum):
    uptime = "uptime"
    health = "health"
    content = "content"
    redirect = "redirect"
    ssl = "ssl"
    domain = "domain"
    wp_cve = "wp_cve"
    new_admin = "new_admin"
    dependency_cve = "dependency_cve"
    blacklist = "blacklist"
    wp_unreachable = "wp_unreachable"


class Severity(str, enum.Enum):
    warning = "warning"
    critical = "critical"


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"))
    check_type: Mapped[CheckType] = mapped_column(Enum(CheckType))
    severity: Mapped[Severity] = mapped_column(Enum(Severity))
    opened_at: Mapped[datetime] = mapped_column(UTCDateTime, server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    cause: Mapped[str] = mapped_column(Text)
    detail_json: Mapped[dict] = mapped_column(JSON, default=dict)
    notified_open_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    notified_close_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    site: Mapped["Site"] = relationship(back_populates="incidents")
