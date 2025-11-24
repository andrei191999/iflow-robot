"""
Holiday utility functions for advanced simulation.

Handles checking if dates are holidays using public calendars (like Romania)
and personal dates, plus finding next valid workdays.
"""

from datetime import date, timedelta
from typing import List, Set
import holidays as holidays_lib
import logging

logger = logging.getLogger(__name__)


def get_holiday_dates(
    year: int,
    public_calendars: List[str],
    personal_dates: List[str]
) -> Set[date]:
    """
    Get set of holiday dates from public calendars and personal dates.

    Args:
        year: Year to check
        public_calendars: List of country codes (e.g., ["RO"])
        personal_dates: List of date strings in ISO format (YYYY-MM-DD)

    Returns:
        Set of holiday dates
    """
    holiday_dates = set()

    # Load public holidays
    for country_code in public_calendars:
        try:
            if country_code == "RO":
                ro_holidays = holidays_lib.Romania(years=year)
                holiday_dates.update(ro_holidays.keys())
                logger.debug(f"Loaded {len(ro_holidays)} holidays for Romania {year}")
        except Exception as e:
            logger.warning(f"Failed to load holidays for {country_code}: {e}")

    # Add personal dates
    for date_str in personal_dates:
        try:
            d = date.fromisoformat(date_str)
            holiday_dates.add(d)
            logger.debug(f"Added personal date: {date_str}")
        except ValueError as e:
            logger.warning(f"Invalid personal date format '{date_str}': {e}")
            continue

    return holiday_dates


def is_holiday(check_date: date, holiday_dates: Set[date]) -> bool:
    """
    Check if a date is a holiday.

    Args:
        check_date: Date to check
        holiday_dates: Set of known holiday dates

    Returns:
        True if the date is a holiday, False otherwise
    """
    return check_date in holiday_dates


def find_next_workday(
    current_date: date,
    holiday_dates: Set[date],
    max_days: int = 30
) -> date:
    """
    Find next non-holiday, non-weekend workday.

    Args:
        current_date: Starting date
        holiday_dates: Set of known holiday dates
        max_days: Maximum days to search ahead

    Returns:
        Next valid workday, or current_date if none found
    """
    next_date = current_date + timedelta(days=1)
    days_checked = 0

    while days_checked < max_days:
        # Skip weekends (5=Saturday, 6=Sunday)
        if next_date.weekday() >= 5:
            next_date += timedelta(days=1)
            days_checked += 1
            continue

        # Skip holidays
        if next_date in holiday_dates:
            next_date += timedelta(days=1)
            days_checked += 1
            continue

        # Found a valid workday
        logger.debug(f"Next workday after {current_date}: {next_date}")
        return next_date

    # Fallback: return original date if can't find workday
    logger.warning(f"Could not find workday after {current_date} within {max_days} days")
    return current_date
