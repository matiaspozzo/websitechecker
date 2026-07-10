from datetime import datetime

from sqlalchemy import JSON, Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.types import UTCDateTime


class BlacklistStatus(Base):
    __tablename__ = "blacklist_statuses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"))
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, server_default=func.now())
    google_safe_browsing_flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    virustotal_flagged: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    raw_json: Mapped[dict] = mapped_column(JSON, default=dict)

    site: Mapped["Site"] = relationship(back_populates="blacklist_statuses")
