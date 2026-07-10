from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TrustedDomain(Base):
    """Domains that a site's iframes/meta-refreshes may point to without being
    flagged as a possible compromise -- analytics, video embeds, virtual tour
    hosts, payment widgets, or a client's own secondary domains. Global (not
    per-site) since the same third-party embeds tend to recur across sites,
    but any domain can be added here as a specific site needs it."""

    __tablename__ = "trusted_domains"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    domain: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
