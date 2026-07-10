from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.types import UTCDateTime


class SslDomainStatus(Base):
    __tablename__ = "ssl_domain_statuses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"))
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, server_default=func.now())
    ssl_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    ssl_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    ssl_error: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    domain_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    whois_error: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    site: Mapped["Site"] = relationship(back_populates="ssl_domain_statuses")
