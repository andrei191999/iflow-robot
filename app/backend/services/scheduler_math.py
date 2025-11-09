from __future__ import annotations
from datetime import datetime, timedelta, date
from typing import Optional, Tuple
from dateutil import tz
import random

from .holidays import (
    WEEK_ORDER,
    is_public_holiday,
    is_personal_holiday,
    matches_exceptions,
    is_blocked_by_hour_windows,
    is_forced_by_hour_windows,
    next_workday,
)

# Constants
MAX_SCHEDULE_SCAN_DAYS = 60

def _parse_hhmm(s: str):
    h, m = s.split(":")
    return int(h), int(m)

def _localize(now_utc: datetime, tz_name: str) -> datetime:
    return now_utc.astimezone(tz.gettz(tz_name))

def _candidate_dt(local_date: date, hhmm: str, tz_name: str) -> datetime:
    h, m = _parse_hhmm(hhmm)
    return datetime(
        local_date.year, local_date.month, local_date.day, h, m, 0, 0, tzinfo=tz.gettz(tz_name)
    )

def compute_next_event(spec: dict, now_utc: Optional[datetime]=None) -> Tuple[str, datetime, str, Optional[str]]:
    """
    Select the next event (checkIn/checkOut) after now_utc considering:
      - enabled weekdays & times
      - jitter +/- minutes
      - public holidays (per 'holidays.publicCalendars' & behavior)
      - personal dates (holidays.personalDates)
      - exceptions.include / exceptions.exclude (dates or datetimes)
      - exceptions.hourWindows (include/exclude by day or date & time window)
    Returns: (event_type, fire_time_utc, local_date_str, location)
    """
    if now_utc is None:
        now_utc = datetime.utcnow().replace(tzinfo=tz.UTC)

    tz_name = spec.get("tz", "Europe/Bucharest")
    week = spec.get("week", {})
    jitter_cfg = spec.get("jitter", {"minutesMinus": 0, "minutesPlus": 0})
    jmin = int(jitter_cfg.get("minutesMinus", 0))
    jmax = int(jitter_cfg.get("minutesPlus", 0))

    hol_cfg = spec.get("holidays", {}) or {}
    calendars = hol_cfg.get("publicCalendars", []) or []
    personal = hol_cfg.get("personalDates", []) or []
    behavior = (hol_cfg.get("behavior") or "skip").lower()  # skip | move_to_next_workday | run_anyway

    exc = spec.get("exceptions", {}) or {}
    ex_inc = exc.get("include", []) or []
    ex_exc = exc.get("exclude", []) or []
    hour_windows = exc.get("hourWindows", []) or []

    # scan forward up to MAX_SCHEDULE_SCAN_DAYS to find something reasonable
    for day_offset in range(0, MAX_SCHEDULE_SCAN_DAYS):
        local_now = _localize(now_utc, tz_name) + timedelta(days=day_offset)
        day_name = WEEK_ORDER[local_now.weekday()]
        day_cfg = week.get(day_name, {}) or {}

        if not day_cfg.get("enabled"):
            continue

        for event_type in ("checkIn", "checkOut"):
            t = day_cfg.get(event_type)
            if not t:
                continue

            loc = day_cfg.get("location")
            cand_local = _candidate_dt(local_now.date(), t, tz_name)

            # If we're examining "today" and we've already passed the time, skip it
            if cand_local <= _localize(now_utc, tz_name):
                continue

            # Holiday handling
            holiday_today = is_public_holiday(cand_local.date(), calendars) or is_personal_holiday(cand_local.date(), personal)

            if holiday_today and behavior == "skip":
                continue
            if holiday_today and behavior == "move_to_next_workday":
                moved_date = next_workday(cand_local.date(), calendars)
                cand_local = _candidate_dt(moved_date, t, tz_name)

            # Exceptions: hour windows (exclude takes effect unless include window forces)
            if is_blocked_by_hour_windows(cand_local, tz_name, hour_windows) and not is_forced_by_hour_windows(cand_local, hour_windows):
                continue

            # Exceptions: exact include/exclude
            force_inc, blocked = matches_exceptions(cand_local, tz_name, ex_inc, ex_exc)
            if blocked and not force_inc:
                continue

            # Apply jitter last
            if jmin or jmax:
                delta_min = random.randint(-abs(jmin), abs(jmax))
                cand_local = cand_local + timedelta(minutes=delta_min)

            cand_utc = cand_local.astimezone(tz.UTC)
            if cand_utc > now_utc:
                return (event_type, cand_utc, cand_local.date().isoformat(), loc)

    # Fallback: one hour later checkIn
    fallback_local = _localize(now_utc + timedelta(hours=1), tz_name)
    return ("checkIn", (now_utc + timedelta(hours=1)), fallback_local.date().isoformat(), None)
