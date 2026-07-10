from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GlobalConfig(Base):
    """Single-row table (id is always 1) holding panel-editable operational config."""

    __tablename__ = "global_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    digest_hour: Mapped[int] = mapped_column(Integer, default=9)
    digest_timezone: Mapped[str] = mapped_column(String(64), default="America/Argentina/Buenos_Aires")
    ssl_alert_days_json: Mapped[list] = mapped_column(JSON, default=lambda: [14, 7, 3])
    domain_alert_days_json: Mapped[list] = mapped_column(JSON, default=lambda: [30, 14, 7])
    panel_base_url: Mapped[str] = mapped_column(String(255), default="http://localhost:8000")
    wpscan_api_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gsb_api_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vt_api_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    healthchecks_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
