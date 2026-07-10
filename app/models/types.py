from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """A DateTime that's always timezone-aware UTC on the Python side.

    SQLite has no real datetime type -- it stores whatever text SQLAlchemy
    hands it and returns naive datetimes on read, even for columns declared
    DateTime(timezone=True). Every value SiteWatch stores is UTC (server_default
    func.now() included, since SQLite's CURRENT_TIMESTAMP is UTC), so re-tagging
    naive values as UTC here is correct, not a workaround -- it just makes the
    Python-side type match what's actually true on disk, so code can freely
    compare loaded timestamps against datetime.now(timezone.utc) without every
    call site needing to know about this SQLite quirk.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
