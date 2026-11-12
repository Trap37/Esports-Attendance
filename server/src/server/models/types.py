from datetime import UTC, datetime

import sqlalchemy as sa

from server.utils.dates import normalize_utc


# TODO: Make use of the tz coercion
class UTCDateTime(sa.TypeDecorator):
    """Store timezone-aware datetimes as UTC."""

    impl = sa.DateTime
    cache_ok = True

    def process_bind_param(
        self,
        value: datetime | None,
        dialect: sa.Dialect,
    ) -> datetime | None:
        if value is None:
            return None

        if value.tzinfo is None:
            raise ValueError('Datetime must be timezone-aware')

        # SQLite does not preserve timezone information.
        # Store the UTC value without tzinfo.
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(
        self,
        value: datetime | None,
        dialect: sa.Dialect,
    ) -> datetime | None:
        if value is None:
            return None

        # SQLite returns naive datetimes, so restore UTC.
        return normalize_utc(value)
