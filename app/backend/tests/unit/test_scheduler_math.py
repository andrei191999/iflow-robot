from datetime import datetime
from dateutil import tz
from freezegun import freeze_time

from services.scheduler_math import compute_next_event

def _base_spec():
    return {
        "tz": "Europe/Bucharest",
        "week": {
            "Mon": {"enabled": True, "checkIn": "09:00", "checkOut": "17:00", "location": "birou"},
            "Tue": {"enabled": True, "checkIn": "09:00", "checkOut": "17:00", "location": "telemunca"},
            "Wed": {"enabled": True, "checkIn": "09:00", "checkOut": "17:00", "location": "birou"},
            "Thu": {"enabled": True, "checkIn": "09:00", "checkOut": "17:00", "location": "telemunca"},
            "Fri": {"enabled": True, "checkIn": "09:00", "checkOut": "16:00", "location": "birou"},
            "Sat": {"enabled": False},
            "Sun": {"enabled": False},
        },
        "jitter": {"minutesMinus": 0, "minutesPlus": 0},
        "holidays": {"publicCalendars": ["RO"], "personalDates": [], "behavior": "skip"},
        "exceptions": {"include": [], "exclude": [], "hourWindows": []},
    }

def _utc(dt_str: str):
    return datetime.fromisoformat(dt_str).replace(tzinfo=tz.UTC)

@freeze_time("2025-10-13 05:59:00+00:00")  # 08:59 local -> next should be 09:00 checkIn
def test_next_event_basic_mon_checkin():
    spec = _base_spec()
    ev, fire_utc, local_date, loc = compute_next_event(spec)
    assert ev == "checkIn"
    # Should be 09:00 local == 06:00 UTC (no jitter)
    assert fire_utc.isoformat().endswith(":00+00:00")
    assert local_date  # "YYYY-MM-DD"
    assert loc == "birou"

@freeze_time("2025-10-13 06:00:00+00:00")
def test_public_holiday_skip_and_move_next_workday():
    spec = _base_spec()
    # Force Monday to be treated as a personal holiday, then "skip"
    spec["holidays"]["personalDates"] = [ "2025-10-13" ]
    spec["holidays"]["behavior"] = "skip"
    ev, _, local_date, _ = compute_next_event(spec)
    assert local_date != "2025-10-13"

    # If behavior is move_to_next_workday, local_date should be Tue 2025-10-14
    spec["holidays"]["behavior"] = "move_to_next_workday"
    ev2, _, local_date2, _ = compute_next_event(spec)
    assert local_date2 >= "2025-10-14"

@freeze_time("2025-10-13 06:00:00+00:00")
def test_hour_window_exclude_then_include():
    spec = _base_spec()
    # Exclude Monday 08:00-10:00, which would block 09:00 checkIn
    spec["exceptions"]["hourWindows"] = [
        {"day": "Mon", "start": "08:00", "end": "10:00", "action": "exclude"}
    ]
    ev, fire_utc, local_date, _ = compute_next_event(spec)
    # Should choose next event (Mon 17:00 or Tue 09:00) – at least not 09:00 Mon
    assert not (local_date == "2025-10-13" and fire_utc.hour == 6)

    # Now add include window that forces run
    spec["exceptions"]["hourWindows"] = [
        {"day": "Mon", "start": "08:50", "end": "09:10", "action": "include"}
    ]
    ev2, fire_utc2, local_date2, _ = compute_next_event(spec)
    # Include window should allow 09:00 event again
    assert local_date2 == "2025-10-13"

@freeze_time("2025-10-13 06:00:00+00:00")
def test_exact_include_exclude_datetime():
    spec = _base_spec()
    # Exclude the exact minute of Monday 09:00 local (06:00 UTC)
    spec["exceptions"]["exclude"] = ["2025-10-13T09:00"]
    ev, fire_utc, local_date, _ = compute_next_event(spec)
    # Next should not be 09:00 Mon (same as previous test)
    assert not (local_date == "2025-10-13" and fire_utc.hour == 6)

    # Force include same minute should override
    spec["exceptions"]["include"] = ["2025-10-13T09:00"]
    ev2, fire_utc2, local_date2, _ = compute_next_event(spec)
    assert local_date2 == "2025-10-13"

@freeze_time("2025-10-13 05:59:00+00:00")
def test_jitter_in_range():
    spec = _base_spec()
    # Only allow positive jitter so we don't slip before 'now'
    spec["jitter"] = {"minutesMinus": 0, "minutesPlus": 7}
    ev, fire_utc, local_date, _ = compute_next_event(spec)
    # 09:00 local baseline is 06:00 UTC; jitter shifts within [0,+7] minutes
    minutes = (fire_utc - _utc("2025-10-13T06:00:00+00:00")).total_seconds() / 60
    assert 0 <= minutes <= 7
    assert ev == "checkIn"
    assert local_date == "2025-10-13"

@freeze_time("2025-10-13 05:59:00+00:00")
def test_negative_jitter_can_skip_to_checkout(monkeypatch):
    spec = _base_spec()
    spec["jitter"] = {"minutesMinus": 5, "minutesPlus": 0}

    # Force the random pick to be -5 minutes so 09:00 -> 08:55 (before now)
    import random
    monkeypatch.setattr(random, "randint", lambda a, b: -5)

    ev, fire_utc, local_date, _ = compute_next_event(spec)
    # The 09:00 check-in was jittered before now, so next event should be checkout
    assert ev == "checkOut"
    # and it should still be same local date
    assert local_date == "2025-10-13"

@freeze_time("2025-12-01 07:59:00+00:00")  # 10:59 Bucharest; Dec 1 is RO National Day (public holiday)
def test_public_holiday_behaviors():
    spec = _base_spec()
    spec["holidays"]["publicCalendars"] = ["RO"]

    # Skip: should not schedule on 2025-12-01
    spec["holidays"]["behavior"] = "skip"
    ev, _, local_date, _ = compute_next_event(spec)
    assert local_date != "2025-12-01"

    # Move to next workday: next non-weekend/non-holiday date
    spec["holidays"]["behavior"] = "move_to_next_workday"
    ev2, _, local_date2, _ = compute_next_event(spec)
    assert local_date2 >= "2025-12-02"

    # Run anyway: allow the same date
    spec["holidays"]["behavior"] = "run_anyway"
    ev3, _, local_date3, _ = compute_next_event(spec)
    assert local_date3 == "2025-12-01"

@freeze_time("2025-10-13 05:59:00+00:00")
def test_exceptions_include_vs_exclude_minute():
    spec = _base_spec()
    # Exclude the exact minute of Mon 09:00 local
    spec["exceptions"]["exclude"] = ["2025-10-13T09:00"]
    ev, fire_utc, local_date, _ = compute_next_event(spec)
    assert not (local_date == "2025-10-13" and fire_utc.hour == 6)

    # Force the same minute via include
    spec["exceptions"]["include"] = ["2025-10-13T09:00"]
    ev2, fire_utc2, local_date2, _ = compute_next_event(spec)
    assert local_date2 == "2025-10-13"

@freeze_time("2025-10-13 05:59:00+00:00")
def test_hour_windows_exclude_then_include():
    spec = _base_spec()
    spec["exceptions"]["hourWindows"] = [
        {"day": "Mon", "start": "08:45", "end": "09:15", "action": "exclude"}
    ]
    ev, fire_utc, local_date, _ = compute_next_event(spec)
    # Should skip 09:00 and pick later
    assert not (local_date == "2025-10-13" and fire_utc.hour == 6)

    # Now include window that overrides block
    spec["exceptions"]["hourWindows"] = [
        {"day": "Mon", "start": "08:50", "end": "09:10", "action": "include"}
    ]
    ev2, fire_utc2, local_date2, _ = compute_next_event(spec)
    assert local_date2 == "2025-10-13"
