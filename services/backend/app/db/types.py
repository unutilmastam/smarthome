"""Custom column types."""

from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """Timezone-aware UTC datetime, identical on SQLite and PostgreSQL.

    Naive datetimes are refused: every timestamp must carry a timezone.
    Values are always returned as aware UTC datetimes.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if not isinstance(value, datetime):
            raise TypeError("UTCDateTime expects datetime")
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Naive datetime is not allowed; use timezone-aware UTC")
        value = value.astimezone(timezone.utc)
        if dialect.name == "sqlite":
            # SQLite has no timezone type: store naive UTC.
            return value.replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
