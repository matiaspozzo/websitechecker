import enum

from sqlalchemy import Boolean, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PatternSeverity(str, enum.Enum):
    warning = "warning"
    critical = "critical"


class SuspiciousPattern(Base):
    __tablename__ = "suspicious_patterns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pattern: Mapped[str] = mapped_column(Text)
    is_regex: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    severity: Mapped[PatternSeverity] = mapped_column(Enum(PatternSeverity), default=PatternSeverity.critical)
