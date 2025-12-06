from datetime import date, timedelta
from typing import List, Set
import holidays as holidays_lib

def get_holiday_dates(
    year: int,
    public_calendars: List[str],
    personal_dates: List[str]
) -> Set[date]:
    """Get set of holiday dates from public calendars and personal dates."""
    holiday_dates = set()

    # Load public holidays
    for country_code in public_calendars:
        # Currently supporting RO, can be extended
        if country_code == "RO":
            ro_holidays = holidays_lib.Romania(years=year)
            holiday_dates.update(ro_holidays.keys())
        # Add other countries here if needed

    # Add personal dates
    for date_str in personal_dates:
        try:
            d = date.fromisoformat(date_str)
            holiday_dates.add(d)
        except ValueError:
            continue

    return holiday_dates

def is_holiday(check_date: date, holiday_dates: Set[date]) -> bool:
    """Check if a date is a holiday."""
    return check_date in holiday_dates

def find_next_workday(
    current_date: date,
    holiday_dates: Set[date],
    max_days: int = 30
) -> date:
    """Find next non-holiday, non-weekend workday."""
    next_date = current_date + timedelta(days=1)
    days_checked = 0

    while days_checked < max_days:
        # Skip weekends (5=Sat, 6=Sun)
        if next_date.weekday() >= 5:
            next_date += timedelta(days=1)
            days_checked += 1
            continue

        # Skip holidays
        if next_date in holiday_dates:
            next_date += timedelta(days=1)
            days_checked += 1
            continue

        return next_date

    # Fallback: return original date if can't find workday
    return current_date
