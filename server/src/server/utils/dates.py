import datetime
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo('America/New_York')


# def to_utc(dt):
#     """Convert a datetime to UTC."""
#     if dt.tzinfo is None:
#         dt = dt.replace(tzinfo=EASTERN)
#     return dt.astimezone(ZoneInfo('UTC'))
def utc_now():
    """Return the current UTC datetime."""
    return datetime.datetime.now(datetime.UTC)


def eastern_now():
    """Return the current Eastern datetime."""
    # return utc_now().astimezone(EASTERN)
    return datetime.datetime.now(EASTERN)


def utc_start_of_today():
    return datetime.datetime.combine(
        eastern_now().date(),
        datetime.time.min,
        EASTERN,
    ).astimezone(datetime.UTC)


def to_eastern_datetime(dt: datetime.datetime):
    """Convert a datetime to Eastern Time."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.UTC)
    return dt.astimezone(EASTERN)


def set_end_of_day(timestamp: datetime.date):
    """Return 5 PM Eastern on the timestamp's local date, in UTC."""
    return datetime.datetime.combine(
        timestamp,
        datetime.time(17, 0),
        tzinfo=EASTERN,
    ).astimezone(datetime.UTC)


def format_timestamp(value: datetime.datetime, *, include_date=True):
    """Format a datetime as YYYY-MM-DD HH:MM AM/PM or HH:MM:SS AM/PM."""
    if include_date:
        return value.strftime('%Y-%m-%d %I:%M %p')
    else:
        return value.strftime('%I:%M:%S %p')


def normalize_utc(value: datetime.datetime):
    if value.tzinfo is None:
        # Assume this was tz unaware from sql model
        return value.replace(tzinfo=datetime.UTC)
    return value.astimezone(datetime.UTC)


def eastern_date_range_to_utc(
    start_date: datetime.date,
    end_date: datetime.date,
):
    if start_date > end_date:
        raise ValueError('start_date must be on or before end_date')

    start = datetime.datetime.combine(
        start_date,
        datetime.time.min,
        EASTERN,
    )

    end = datetime.datetime.combine(
        end_date + datetime.timedelta(days=1),
        datetime.time.min,
        EASTERN,
    )

    return (
        start.astimezone(datetime.UTC),
        end.astimezone(datetime.UTC),
    )


def utc_time_is_before_today(utc_time: datetime.datetime):
    if utc_time.tzinfo is None or utc_time.utcoffset() is None:
        raise ValueError('utc_time must be timezone-aware')

    if utc_time.utcoffset().total_seconds() != 0:
        raise ValueError('utc_time must be in UTC')

    return utc_time < utc_start_of_today()


# def parse_date_range(start: str, end: str):
#     try:
#         start_date = datetime.date.fromisoformat(start)
#         end_date = datetime.date.fromisoformat(end)
#     except ValueError:
#         return None, None, ('start and end must be YYYY-MM-DD', 400)

#     if start_date.isoformat() != start or end_date.isoformat() != end:
#         return None, None, ('start and end must be YYYY-MM-DD', 400)
#     if start_date > end_date:
#         return None, None, ('start must be on or before end', 400)

#     return start_date, end_date, None
