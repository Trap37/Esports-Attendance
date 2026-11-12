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
    return utc_now().astimezone(EASTERN)


def utc_start_of_today():
    return datetime.datetime.combine(
        eastern_now(),
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


def to_eastern_strftime(value: datetime.datetime):
    """Returns datetime in EST formatted as YYYY-MM-DD HH:MM AM/PM"""
    return to_eastern_datetime(value).strftime('%Y-%m-%d %I:%M %p')
