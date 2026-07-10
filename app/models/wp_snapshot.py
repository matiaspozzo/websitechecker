from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class WpSnapshot(Base):
    __tablename__ = "wp_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    core_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    core_update_available: Mapped[str | None] = mapped_column(String(50), nullable=True)
    php_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    plugins_json: Mapped[list] = mapped_column(JSON, default=list)
    themes_json: Mapped[list] = mapped_column(JSON, default=list)
    admin_usernames_json: Mapped[list] = mapped_column(JSON, default=list)
    raw_report_json: Mapped[dict] = mapped_column(JSON, default=dict)

    site: Mapped["Site"] = relationship(back_populates="wp_snapshots")
