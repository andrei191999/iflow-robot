import pytest
from datetime import date, datetime
from services.holiday_utils import get_holiday_dates, is_holiday, find_next_workday

def test_get_holiday_dates():
    # Test Romania holidays
    holidays = get_holiday_dates(2025, ["RO"], [])
    assert date(2025, 12, 1) in holidays  # National Day
    assert date(2025, 12, 25) in holidays # Christmas

    # Test personal dates
    personal = ["2025-11-25", "2025-01-01"]
    holidays = get_holiday_dates(2025, [], personal)
    assert date(2025, 11, 25) in holidays
    assert date(2025, 1, 1) in holidays

def test_is_holiday():
    holidays = {date(2025, 12, 1)}
    assert is_holiday(date(2025, 12, 1), holidays)
    assert not is_holiday(date(2025, 12, 2), holidays)

def test_find_next_workday():
    # Friday -> Monday (skip weekend)
    friday = date(2023, 11, 24)
    next_day = find_next_workday(friday, set())
    assert next_day == date(2023, 11, 27) # Monday

    # Holiday on Monday -> Tuesday
    monday = date(2023, 11, 27)
    holidays = {date(2023, 11, 28)} # Tuesday is holiday
    next_day = find_next_workday(monday, holidays)
    assert next_day == date(2023, 11, 29) # Wednesday
