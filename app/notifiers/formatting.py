from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

BUENOS_AIRES = ZoneInfo("America/Argentina/Buenos_Aires")

SEVERITY_EMOJI = {
    "critical": "\U0001F534",  # red circle
    "warning": "\U0001F7E0",  # orange circle
}

STATUS_EMOJI = {
    "up": "\U0001F7E2",  # green circle
    "down": "\U0001F534",
    "paused": "⏸️",
}


def format_timestamp(dt: datetime) -> str:
    local = dt.astimezone(BUENOS_AIRES) if dt.tzinfo else dt.replace(tzinfo=BUENOS_AIRES)
    return local.strftime("%Y-%m-%d %H:%M:%S %Z")


def format_duration(delta: timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if not parts:
        parts.append(f"{seconds}s")
    return " ".join(parts)


def site_link(panel_base_url: str, site_id: int) -> str:
    return f"{panel_base_url.rstrip('/')}/sites/{site_id}"
