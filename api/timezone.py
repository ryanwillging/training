"""Shared timezone utilities for consistent time handling across all pages.

All pages should use these functions instead of datetime.now() or date.today()
to ensure Eastern timezone is used consistently.
"""

from datetime import datetime, timedelta, timezone


# Eastern timezone offset
def _is_dst(utc_now: datetime) -> bool:
    """Check if Eastern time is in DST (roughly March-November)."""
    month = utc_now.month
    day = utc_now.day
    # DST starts 2nd Sunday in March, ends 1st Sunday in November
    # Simplified: March 10 - November 3 (approximate)
    if month < 3 or month > 11:
        return False
    if month > 3 and month < 11:
        return True
    # March: DST starts around the 10th
    if month == 3:
        return day >= 10
    # November: DST ends around the 3rd
    return day < 3


def get_eastern_now() -> datetime:
    """Get current datetime in Eastern time (EST/EDT).

    Use this instead of datetime.now() for consistent timezone handling.
    """
    utc_now = datetime.now(timezone.utc)
    offset = timedelta(hours=-4 if _is_dst(utc_now) else -5)
    eastern_tz = timezone(offset)
    return utc_now.astimezone(eastern_tz)


def get_eastern_today():
    """Get current date in Eastern time.

    Use this instead of date.today() for consistent timezone handling.
    """
    return get_eastern_now().date()


def format_datetime(dt: datetime = None, fmt: str = '%B %d, %Y at %I:%M %p') -> str:
    """Format a datetime for display. Defaults to current Eastern time."""
    if dt is None:
        dt = get_eastern_now()
    return dt.strftime(fmt)


def format_date(d=None, fmt: str = '%A, %B %d') -> str:
    """Format a date for display. Defaults to current Eastern date."""
    if d is None:
        d = get_eastern_today()
    return d.strftime(fmt)
