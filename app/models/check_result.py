from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.incident import CheckType
from app.models.types import UTCDateTime


class CheckResult(Base):
    __tablename__ = "check_results"
    __table_args__ = (Index("ix_check_results_site_timestamp", "site_id", "timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"))
    check_type: Mapped[CheckType] = mapped_column(Enum(CheckType))
    success: Mapped[bool]
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, server_default=func.now())
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    site: Mapped["Site"] = relationship(back_populates="check_results")
