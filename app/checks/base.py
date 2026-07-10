from dataclasses import dataclass, field
from typing import Protocol

import aiohttp
from sqlalchemy.orm import Session

from app.models.site import Site


@dataclass
class CheckOutcome:
    """Result of a single check run for a single site."""

    success: bool
    check_type: str
    latency_ms: int | None = None
    status_code: int | None = None
    error_message: str | None = None
    # Set when this outcome should open/refresh an incident.
    severity: str | None = None  # "warning" | "critical"
    cause: str | None = None
    detail: dict = field(default_factory=dict)


class Checker(Protocol):
    check_type: str

    async def run(self, site: Site, db: Session, http: aiohttp.ClientSession) -> CheckOutcome: ...
