from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.types import UTCDateTime


class DependencyAudit(Base):
    __tablename__ = "dependency_audits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"))
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, server_default=func.now())
    tool: Mapped[str] = mapped_column(String(20))  # "composer" | "npm"
    raw_json: Mapped[dict] = mapped_column(JSON, default=dict)
    high_critical_count: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    site: Mapped["Site"] = relationship(back_populates="dependency_audits")
