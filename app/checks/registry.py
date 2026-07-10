from typing import TYPE_CHECKING

from app.checks.base import Checker
from app.models.site import MonitoringMode, SiteType

if TYPE_CHECKING:
    from app.models.site import Site

_registry: dict[str, Checker] = {}

# check_type -> which site types it applies to (None = all types)
_APPLIES_TO: dict[str, set[SiteType] | None] = {}

# Checks that still run for a "basic" (uptime + SSL/domain only) site.
BASIC_MODE_CHECK_TYPES = ["uptime", "ssl_domain"]


def register(checker: Checker, applies_to: set[SiteType] | None = None) -> None:
    _registry[checker.check_type] = checker
    _APPLIES_TO[checker.check_type] = applies_to


def get_checker(check_type: str) -> Checker:
    return _registry[check_type]


def all_check_types() -> list[str]:
    return list(_registry.keys())


def check_types_for_site_type(site_type: SiteType) -> list[str]:
    return [
        check_type
        for check_type, applies_to in _APPLIES_TO.items()
        if applies_to is None or site_type in applies_to
    ]


def applicable_check_types(site: "Site") -> list[str]:
    """Which check_types should actually run for this site, accounting for both
    its type (wordpress/laravel/nextjs) and monitoring mode (full vs basic)."""
    if site.monitoring_mode == MonitoringMode.basic:
        return list(BASIC_MODE_CHECK_TYPES)
    return check_types_for_site_type(site.type)


def load_all_checkers() -> None:
    """Import every check module so its @register call runs. Call once at startup."""
    from app.checks import (  # noqa: F401
        blacklists,
        content_integrity,
        laravel_nextjs,
        ssl_domain,
        uptime,
        wordpress,
    )
