from __future__ import annotations
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple
from dateutil import tz
import holidays as pyholidays

WEEK_ORDER = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

def _parse_iso_date(s: str) -> Optional[date]:
    try:
        return date.fromisoformat(s)
    except Exception:
        return None

def _parse_iso_dt_local(s: str, tz_name: str) -> Optional[datetime]:
    try:
        # Accept both "YYYY-MM-DDTHH:MM" and with seconds
        if "T" not in s:
            return None
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz.gettz(tz_name))
        return dt.astimezone(tz.gettz(tz_name))
    except Exception:
        return None

def is_public_holiday(local_d: date, calendars: List[str]) -> bool:
    """Return True if local date is holiday in ANY of the given ISO country codes."""
    for code in calendars or []:
        try:
            if local_d in pyholidays.country_holidays(code):
                return True
        except Exception:
            continue
    return False

def is_personal_holiday(local_d: date, personal_dates: List[str]) -> bool:
    for s in personal_dates or []:
        d = _parse_iso_date(s)
        if d and d == local_d:
            return True
    return False

def _time_in_window(local_dt: datetime, start_hhmm: str, end_hhmm: str) -> bool:
    """Check if datetime is within the time window defined by start and end HH:MM strings."""
    h1, m1 = map(int, start_hhmm.split(":"))
    h2, m2 = map(int, end_hhmm.split(":"))
    t = local_dt.time()
    return (t >= datetime(local_dt.year, local_dt.month, local_dt.day, h1, m1).time() and
            t <= datetime(local_dt.year, local_dt.month, local_dt.day, h2, m2).time())

def is_blocked_by_hour_windows(local_dt: datetime, tz_name: str, hour_windows: List[dict]) -> bool:
    """Return True if an EXCLUDE window matches. INCLUDE windows are handled separately."""
    dow = WEEK_ORDER[local_dt.weekday()]
    ymd = local_dt.date().isoformat()
    for hw in hour_windows or []:
        if hw.get("action","exclude") != "exclude":
            continue
        day_key = hw.get("day","")
        if day_key not in (dow, ymd):
            continue
        if _time_in_window(local_dt, hw["start"], hw["end"]):
            return True
    return False

def is_forced_by_hour_windows(local_dt: datetime, hour_windows: List[dict]) -> bool:
    """Return True if an INCLUDE window matches (forces run even if otherwise skipped)."""
    dow = WEEK_ORDER[local_dt.weekday()]
    ymd = local_dt.date().isoformat()
    for hw in hour_windows or []:
        if hw.get("action") != "include":
            continue
        day_key = hw.get("day","")
        if day_key not in (dow, ymd):
            continue
        if _time_in_window(local_dt, hw["start"], hw["end"]):
            return True
    return False

def matches_exceptions(local_dt: datetime, tz_name: str, include: List[str], exclude: List[str]) -> Tuple[bool, bool]:
    """
    Returns (force_include, blocked) based on include/exclude exact date/datetime matches.
    - Date match (YYYY-MM-DD): whole day.
    - Datetime match (YYYY-MM-DDTHH:MM[..]): exact minute.
    Exclude wins over include in the caller if both are True.
    """
    local_date = local_dt.date()
    force = False
    block = False

    for s in include or []:
        d = _parse_iso_date(s)
        if d and d == local_date:
            force = True
        dt = _parse_iso_dt_local(s, tz_name)
        if dt and dt.replace(second=0, microsecond=0) == local_dt.replace(second=0, microsecond=0):
            force = True

    for s in exclude or []:
        d = _parse_iso_date(s)
        if d and d == local_date:
            block = True
        dt = _parse_iso_dt_local(s, tz_name)
        if dt and dt.replace(second=0, microsecond=0) == local_dt.replace(second=0, microsecond=0):
            block = True

    return (force, block)

def next_workday(local_d: date, calendars: List[str], max_days: int = 365) -> date:
    """
    Move to next non-weekend, non-public-holiday date.

    Args:
        local_d: Starting date
        calendars: List of ISO country codes for public holiday calendars
        max_days: Maximum days to search forward (default 365)

    Returns:
        Next valid workday

    Raises:
        RuntimeError: If no workday found within max_days limit
    """
    d = local_d
    days_checked = 0
    while days_checked < max_days:
        d = d + timedelta(days=1)
        days_checked += 1
        if d.weekday() >= 5:
            continue
        if is_public_holiday(d, calendars):
            continue
        return d
    raise RuntimeError(f"No workday found within {max_days} days from {local_d}")
