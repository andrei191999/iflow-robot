"""
Demo and simulation endpoints for testing iFlow automation.

Provides endpoints to run simulations with various modes and capture detailed logs.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List
from playwright.sync_api import sync_playwright

from fastapi import APIRouter, Depends, HTTPException

from core.security import require_firebase_user
from schemas.demo import (
    DemoRequest,
    DemoResult,
    PublicSimulationRequest,
    PublicSimulationResult,
    AdvancedSimulationRequest,
    AdvancedSimulationResult,
    AdvancedSimulationEvent,
    AdvancedSimulationSummary
)
from services.screenshot_storage import get_screenshot_storage
from services.iso_task_enhanced import run_iso_check_enhanced, run_simulation_sequence
from services.holiday_utils import get_holiday_dates, is_holiday, find_next_workday
from services.mock_iflow.state import set_mock_behavior
from services.scheduler_math import compute_next_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/simulation", tags=["Simulation"])


@router.post("/run", response_model=DemoResult)
async def run_simulation(
    request: DemoRequest,
    user: Dict = Depends(require_firebase_user)
):
    """
    Run an iFlow simulation with specified parameters.

    This endpoint allows testing the automation system with various modes:
    - **visual**: Opens browser window to watch execution
    - **screenshot**: Captures screenshots at each step (headless)
    - **backend**: Production mode (headless, no screenshots)

    Speed options control delays between steps:
    - **slow**: 2 second delays (good for watching)
    - **normal**: 0.5 second delays
    - **fast**: No artificial delays

    Can use either the real iFlow server or a mock server for testing.

    **Authentication required**: Valid Firebase user token
    """
    uid = user.get("uid")
    timestamp = datetime.utcnow().isoformat().replace(":", "-").replace(".", "-")

    logger.info(
        f"Starting simulation for user {uid}: "
        f"scenario={request.scenario}, mode={request.mode}, speed={request.speed}, "
        f"use_mock={request.use_mock}"
    )

    # Configure mock server if requested
    mock_url = None
    if request.use_mock:
        # Configure mock behavior
        behavior = request.mock_behavior or "success"
        set_mock_behavior(behavior=behavior)
        logger.info(f"Mock server configured with behavior: {behavior}")

        # Use mock URL
        # In production this would be the deployed backend URL + /mock-iflow
        # For local dev, assume running on same server
        import os
        port = os.getenv("PORT", "8000")
        # Use localhost for internal loopback to mock server to avoid external routing issues
        mock_url = f"http://127.0.0.1:{port}/mock-iflow/login"
        logger.info(f"Using mock iFlow at: {mock_url}")

    # Determine settings based on mode
    capture_screenshots = request.mode in ["screenshot", "visual"]
    headless = request.mode != "visual"

    # Get screenshot storage if needed
    screenshot_storage = None
    if capture_screenshots:
        screenshot_storage = get_screenshot_storage()

    # Prepare user settings
    user_settings = {
        "iflowUrl": mock_url or "https://app.hriflow.ro/#/dashboard",
        "iflowUsername": "demo@example.com",  # Mock credentials
        "iflowPassword": "demo123",
        "iflowHeadless": headless,
        "iflowTimeout": 30000
    }

    # If not using mock, we need real credentials
    if not request.use_mock:
        # In production, fetch from Firestore settings collection
        # For now, require mock mode
        raise HTTPException(
            status_code=400,
            detail="Real iFlow testing requires valid credentials. Please use mock mode (use_mock=true) for demo."
        )

    # Convert scenario to event type
    event_type = "checkIn" if request.scenario == "check-in" else "checkOut"

    # Run the simulation (in thread since Playwright is sync)
    try:
        status, message, steps, duration_ms = await asyncio.to_thread(
            run_iso_check_enhanced,
            event_type=event_type,
            location=request.location,
            user_settings=user_settings,
            capture_screenshots=capture_screenshots,
            speed=request.speed,
            use_mock_url=mock_url,
            screenshot_storage=screenshot_storage,
            uid=uid,
            timestamp=timestamp
        )

        # Build result
        result = DemoResult(
            success=(status == "success"),
            duration_ms=duration_ms,
            step_count=len(steps),
            scenario=request.scenario,
            location=request.location,
            mode=request.mode,
            steps=steps,
            screenshots=[step.screenshot_url for step in steps if step.screenshot_url],
            summary=_generate_summary(
                status,
                request.scenario,
                request.location,
                duration_ms,
                len(steps),
                date_val=datetime.now().strftime("%d/%m/%Y")
            ),
            error=message if status != "success" else None
        )

        logger.info(
            f"Simulation completed for user {uid}: "
            f"success={result.success}, duration={duration_ms}ms, steps={len(steps)}"
        )

        return result

    except Exception as e:
        logger.error(f"Simulation failed for user {uid}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Simulation failed: {str(e)}"
        )


def _generate_summary(
    status: str,
    scenario: str,
    location: str,
    duration_ms: int,
    step_count: int,
    time_val: str = "",
    date_val: str = "",
    actual_time: str = ""
) -> str:
    """Generate human-readable summary of simulation run."""
    # Use actual_time if provided, otherwise fall back to time_val (for backward compatibility)
    actual = actual_time if actual_time else time_val

    # Multi-line format matching advanced simulation
    if time_val:
        timing_details = f"Scheduled action: {time_val}, Actual action time: {actual}\n"
        timing_details += f"Scheduled {scenario} time: {time_val}, Actual {scenario} time: {actual}"
    else:
        timing_details = ""

    if status == "success":
        if timing_details:
            return timing_details
        else:
            return f"Successfully completed {scenario} at {location} in {duration_ms}ms ({step_count} steps)."
    else:
        error_msg = f"Failed to complete {scenario}"
        if timing_details:
            return f"{error_msg}\n{timing_details}"
        else:
            return f"{error_msg} after {duration_ms}ms ({step_count} steps executed before failure)."


@router.post("/run-public", response_model=PublicSimulationResult)
async def run_public_simulation(request: PublicSimulationRequest):
    """
    Run a public simulation with both check-in and check-out (no auth required).
    """
    timestamp = datetime.utcnow().isoformat().replace(":", "-").replace(".", "-")
    uid = "public-demo"
    logger.info(f"Starting public simulation: mode={request.mode}")

    # Configure mock
    set_mock_behavior(behavior="success")
    import os
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    mock_url_base = f"{base_url}/mock-iflow/login"

    checkin_time = request.checkInTime
    checkout_time = request.checkOutTime

    # Store settings
    capture_screenshots = request.mode in ["screenshot", "visual"]
    headless = request.mode != "visual"

    screenshot_storage = None
    if capture_screenshots:
        screenshot_storage = get_screenshot_storage()

    user_settings = {
        "iflowUrl": mock_url_base,
        "iflowUsername": "demo@example.com",
        "iflowPassword": "demo123",
        "iflowHeadless": headless,
        "iflowTimeout": 30000
    }

    total_start_time = datetime.utcnow()
    current_date_str = datetime.now().strftime("%d/%m/%Y")

    try:
        checkin_result_tuple, checkout_result_tuple = await asyncio.to_thread(
            run_simulation_sequence,
            location=request.location,
            checkin_time=checkin_time,
            checkout_time=checkout_time,
            user_settings=user_settings,
            capture_screenshots=capture_screenshots,
            speed=request.speed,
            mock_url_base=mock_url_base,
            screenshot_storage=screenshot_storage,
            uid=uid,
            timestamp=timestamp,
            date=current_date_str
        )

        # Unpack results
        checkin_status, checkin_msg, checkin_steps, checkin_dur = checkin_result_tuple
        checkout_status, checkout_msg, checkout_steps, checkout_dur = checkout_result_tuple

        # Normalize status
        checkin_success = (checkin_status == "success")
        checkout_success = (checkout_status == "success")

        checkin_result = DemoResult(
            success=checkin_success,
            duration_ms=checkin_dur,
            step_count=len(checkin_steps),
            scenario="check-in",
            location=request.location,
            mode=request.mode,
            steps=checkin_steps,
            screenshots=[step.screenshot_url for step in checkin_steps if step.screenshot_url],
            summary=_generate_summary(checkin_status, "check-in", request.location, checkin_dur, len(checkin_steps), time_val=checkin_time, date_val=current_date_str),
            error=checkin_msg if not checkin_success else None
        )

        checkout_result = DemoResult(
            success=checkout_success,
            duration_ms=checkout_dur,
            step_count=len(checkout_steps),
            scenario="check-out",
            location=request.location,
            mode=request.mode,
            steps=checkout_steps,
            screenshots=[step.screenshot_url for step in checkout_steps if step.screenshot_url],
            summary=_generate_summary(checkout_status, "check-out", request.location, checkout_dur, len(checkout_steps), time_val=checkout_time, date_val=current_date_str),
            error=checkout_msg if not checkout_success else None
        )

    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    total_duration = int((datetime.utcnow() - total_start_time).total_seconds() * 1000)

    # Detailed summary
    summary_parts = []
    summary_parts.append(f"Simulation completed in {total_duration}ms.")

    if checkin_result.success:
        summary_parts.append(f"Check-in: Success ({checkin_time}).")
    else:
        summary_parts.append(f"Check-in: Failed.")

    if checkout_result.success:
        summary_parts.append(f"Check-out: Success ({checkout_time}).")
    else:
        summary_parts.append(f"Check-out: Failed.")

    result = PublicSimulationResult(
        success=checkin_result.success and checkout_result.success,
        total_duration_ms=total_duration,
        checkin_result=checkin_result,
        checkout_result=checkout_result,
        summary=" ".join(summary_parts)
    )

    logger.info(f"Public simulation completed: success={result.success}, duration={total_duration}ms")

    return result



def _run_advanced_simulation_sync(
    request: AdvancedSimulationRequest,
    uid: str,
    timestamp: str,
    user_settings: Dict,
    mock_url: str,
    screenshot_storage,
    start_date: datetime,
    end_date: datetime,
    spec: Dict
) -> AdvancedSimulationResult:
    """
    Synchronous implementation of advanced simulation to run in a single thread.
    This ensures Playwright objects are created and used in the same thread.
    """
    from datetime import timedelta, timezone
    import random

    logger.info(f"Starting synchronous simulation for {uid}")

    # Collect all events
    events: List[AdvancedSimulationEvent] = []
    sample_screenshots = []
    should_run_live = request.mode in ["screenshot"]

    # Initialize browser resources - NOT used for live events
    # Each event will get its own browser instance
    playwright = None
    browser = None
    context = None
    page = None


    # Iterate through each day
    current_date = start_date
    run_count = 0
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    # Load holidays
    holidays_config = spec.get("holidays", {})
    holiday_dates = set()
    if holidays_config:
        years_to_check = set([start_date.year, end_date.year])
        for year in years_to_check:
            holiday_dates.update(get_holiday_dates(
                year=year,
                public_calendars=holidays_config.get("publicCalendars", []),
                personal_dates=holidays_config.get("personalDates", [])
            ))

    # Initialize counters
    skipped_events = 0

    while current_date < end_date:
        day_of_week = current_date.weekday()
        day_name = day_names[day_of_week]
        event_date_local = current_date.strftime("%Y-%m-%d")

        # Check if enabled
        day_config = spec.get("week", {}).get(day_name, {})
        is_enabled = day_config.get("enabled", False)

        if is_enabled:
            # Check if current_date is a holiday
            is_holiday_today = False
            if holidays_config and is_holiday(current_date.date(), holiday_dates):
                is_holiday_today = True
                behavior = holidays_config.get("behavior", "skip")

                if behavior == "skip":
                    # Skip this day
                    skipped_events += 2  # Both checkin and checkout skipped

                    # Add skipped events to the list so they appear in UI
                    events.append(AdvancedSimulationEvent(
                        date=event_date_local,
                        time="00:00",
                        event_type="checkIn",
                        location="holiday",
                        status="skipped",
                        reason="Skipped due to holiday",
                        scheduledAt=current_date.isoformat(),
                        localDate=event_date_local
                    ))
                    events.append(AdvancedSimulationEvent(
                        date=event_date_local,
                        time="00:00",
                        event_type="checkOut",
                        location="holiday",
                        status="skipped",
                        reason="Skipped due to holiday",
                        scheduledAt=current_date.isoformat(),
                        localDate=event_date_local
                    ))

                    current_date += timedelta(days=1)
                    continue
                elif behavior == "move_to_next_workday":
                    # Move to next workday
                    next_workday = find_next_workday(current_date.date(), holiday_dates)
                    # Create a new datetime for the next workday
                    current_date = datetime.combine(next_workday, datetime.min.time()).replace(tzinfo=current_date.tzinfo)
                    # Re-check this day's config (continue loop with new date)
                    continue
                # elif behavior == "force_checkin": proceed normally

            checkin_time_str = day_config.get("checkIn", "09:00")
            checkout_time_str = day_config.get("checkOut", "17:00")
            location = day_config.get("location", "telemunca")

            # Apply jitter
            jitter_config = request.jitter

            # Initialize jitter values
            checkin_jitter_minutes = 0
            checkout_jitter_minutes = 0
            exec_checkin_jitter_minutes = 0
            exec_checkout_jitter_minutes = 0

            # Time Jitter (affects the time TYPED in the form)
            if jitter_config and jitter_config.time:
                checkin_jitter_minutes = random.randint(-jitter_config.timeRange, jitter_config.timeRange)
                checkout_jitter_minutes = random.randint(-jitter_config.timeRange, jitter_config.timeRange)

            # Execution Jitter (affects WHEN the script would run)
            if jitter_config and jitter_config.execution:
                exec_checkin_jitter_minutes = random.randint(-jitter_config.executionRange, jitter_config.executionRange)
                exec_checkout_jitter_minutes = random.randint(-jitter_config.executionRange, jitter_config.executionRange)

            # Calculate times
            checkin_hour, checkin_min = map(int, checkin_time_str.split(":"))
            checkout_hour, checkout_min = map(int, checkout_time_str.split(":"))

            checkin_base = current_date.replace(hour=checkin_hour, minute=checkin_min, second=0, microsecond=0)
            checkout_base = current_date.replace(hour=checkout_hour, minute=checkout_min, second=0, microsecond=0)

            # Apply Time Jitter
            checkin_dt = checkin_base + timedelta(minutes=checkin_jitter_minutes)
            checkout_dt = checkout_base + timedelta(minutes=checkout_jitter_minutes)

            # Apply Execution Jitter (for "scheduledAt" visualization)
            checkin_exec_dt = checkin_dt + timedelta(minutes=exec_checkin_jitter_minutes)
            checkout_exec_dt = checkout_dt + timedelta(minutes=exec_checkout_jitter_minutes)

            checkin_utc = checkin_exec_dt.astimezone(timezone.utc)
            checkout_utc = checkout_exec_dt.astimezone(timezone.utc)

            # Run CheckIn and CheckOut as a pair using run_simulation_sequence
            # This keeps the browser open between the two events
            max_live_events = 6 if request.mode == "visual" else 3
            if run_count < max_live_events and should_run_live:
                try:
                    checkin_time_str_fmt = checkin_dt.strftime("%H:%M")
                    checkout_time_str_fmt = checkout_dt.strftime("%H:%M")
                    date_str = current_date.strftime("%d/%m/%Y")

                    # Use run_simulation_sequence to keep browser open for both events
                    checkin_result_tuple, checkout_result_tuple = run_simulation_sequence(
                        location=location,
                        checkin_time=checkin_time_str_fmt,
                        checkout_time=checkout_time_str_fmt,
                        user_settings=user_settings,
                        capture_screenshots=(request.mode == "screenshot"),
                        speed=request.speed or "fast",
                        mock_url_base=mock_url,  # Just the base URL without query params
                        screenshot_storage=screenshot_storage,
                        uid=uid,
                        timestamp=f"{timestamp}-day{run_count//2}",
                        date=date_str  # Pass date separately
                    )

                    # Unpack checkin results
                    checkin_status_str, checkin_message, checkin_steps, checkin_duration = checkin_result_tuple
                    checkin_status = "success" if checkin_status_str == "success" else "failure"

                    # Unpack checkout results
                    checkout_status_str, checkout_message, checkout_steps, checkout_duration = checkout_result_tuple
                    checkout_status = "success" if checkout_status_str == "success" else "failure"

                    # Collect screenshots per event
                    checkin_screenshots = [step.screenshot_url for step in checkin_steps if step.screenshot_url]
                    checkout_screenshots = [step.screenshot_url for step in checkout_steps if step.screenshot_url]

                    # Also add to global sample list (limit total global samples if needed, but we reduced capture rate)
                    sample_screenshots.extend(checkin_screenshots)
                    sample_screenshots.extend(checkout_screenshots)

                    # Update message with detailed timing info (User requested detailed multi-line format without Success prefix)
                    checkin_exec_fmt = checkin_exec_dt.strftime("%H:%M")
                    checkout_exec_fmt = checkout_exec_dt.strftime("%H:%M")

                    c_msg = checkin_message or 'Success'
                    checkin_details = f"Scheduled action: {checkin_time_str}, Actual action time: {checkin_exec_fmt}\nScheduled check/in time: {checkin_time_str}, Actual check/in time: {checkin_time_str_fmt}"
                    if c_msg == 'Success':
                        checkin_message = checkin_details
                    else:
                        checkin_message = f"{c_msg}\n{checkin_details}"

                    co_msg = checkout_message or 'Success'
                    checkout_details = f"Scheduled action: {checkout_time_str}, Actual action time: {checkout_exec_fmt}\nScheduled check/out time: {checkout_time_str}, Actual check/out time: {checkout_time_str_fmt}"
                    if co_msg == 'Success':
                        checkout_message = checkout_details
                    else:
                        checkout_message = f"{co_msg}\n{checkout_details}"

                except Exception as e:
                    logger.error(f"Day simulation failed: {e}")
                    checkin_status = "failure"
                    checkin_message = str(e)
                    checkout_status = "failure"
                    checkout_message = str(e)
                    checkin_screenshots = []
                    checkout_screenshots = []
            else:
                # Simulated events (not actually run)
                if request.mode == "visual":
                    checkin_status = "planned"
                    checkout_status = "planned"
                else:
                    checkin_status = "success"
                    checkout_status = "success"

                checkin_time_str_fmt = checkin_dt.strftime("%H:%M")
                checkout_time_str_fmt = checkout_dt.strftime("%H:%M")

                checkin_exec_fmt = checkin_exec_dt.strftime("%H:%M")
                checkout_exec_fmt = checkout_exec_dt.strftime("%H:%M")

                checkin_message = f"Scheduled action: {checkin_time_str}, Actual action time: {checkin_exec_fmt}\nScheduled check/in time: {checkin_time_str}, Actual check/in time: {checkin_time_str_fmt}"
                checkout_message = f"Scheduled action: {checkout_time_str}, Actual action time: {checkout_exec_fmt}\nScheduled check/out time: {checkout_time_str}, Actual check/out time: {checkout_time_str_fmt}"

                checkin_screenshots = []
                checkout_screenshots = []

                # Jitter info removed from text as per request

            # Add both events
            events.append(AdvancedSimulationEvent(
                date=event_date_local,
                time=checkin_dt.strftime("%H:%M"),
                event_type="checkIn",
                location=location,
                status=checkin_status,
                reason=checkin_message,
                scheduledAt=checkin_utc.isoformat(),
                localDate=event_date_local,
                screenshots=checkin_screenshots
            ))

            events.append(AdvancedSimulationEvent(
                date=event_date_local,
                time=checkout_dt.strftime("%H:%M"),
                event_type="checkOut",
                location=location,
                status=checkout_status,
                reason=checkout_message,
                scheduledAt=checkout_utc.isoformat(),
                localDate=event_date_local,
                screenshots=checkout_screenshots
            ))

            run_count += 2  # Increment by 2 since we ran both checkin and checkout

        current_date += timedelta(days=1)

    # Calculate stats
    total_events = len(events)
    # Count success/failure from ALL events (including simulated ones)
    success_events = len([e for e in events if e.status == "success"])
    failed_events = len([e for e in events if e.status == "failure"])
    # Skipped count is now coming from the events list directly
    skipped_count_from_list = len([e for e in events if e.status == "skipped"])

    success_rate = (success_events / total_events * 100) if total_events > 0 else 0

    return AdvancedSimulationResult(
        success=True,
        total_events=total_events,
        successful_events=success_events,
        failed_events=failed_events,
        skipped_events=skipped_count_from_list,
        success_rate=success_rate,
        events=events,
        sample_screenshots=sample_screenshots,
        holiday_handling={"holidaysSkipped": skipped_count_from_list, "exceptionsApplied": 0},
        summary=AdvancedSimulationSummary(
            totalEvents=total_events,
            successCount=success_events,
            failureCount=failed_events,
            holidaysSkipped=skipped_count_from_list,
            dateRange={"start": start_date.strftime("%Y-%m-%d"), "end": end_date.strftime("%Y-%m-%d")}
        ),
        duration_ms=0
    )


@router.post("/run-advanced", response_model=AdvancedSimulationResult)
async def run_advanced_simulation(
    request: AdvancedSimulationRequest,
    user: Dict = Depends(require_firebase_user)
):
    """
    Run an advanced simulation over a time period with full schedule spec.
    """
    from datetime import datetime, timedelta, timezone
    from zoneinfo import ZoneInfo

    uid = user.get("uid")
    timestamp = datetime.utcnow().isoformat().replace(":", "-").replace(".", "-")

    logger.info(f"Starting advanced simulation for user {uid}")

    # Determine simulation period
    duration_days = {
        "1-week": 7,
        "1-month": 30,
        "3-months": 90
    }
    days = duration_days.get(request.duration, 7)

    # Get timezone from spec
    spec = request.spec
    tz_str = spec.get("tz", "Europe/Bucharest")
    tz = ZoneInfo(tz_str)

    # Start from today
    start_date = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=days)

    # Configure mock server
    set_mock_behavior(behavior="success")
    import os
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    mock_url = f"{base_url}/mock-iflow/login"

    # Screenshot storage
    screenshot_storage = None
    if request.mode == "screenshot":
        screenshot_storage = get_screenshot_storage()

    # Prepare settings
    user_settings = {
        "iflowUrl": mock_url,
        "iflowUsername": "demo@example.com",
        "iflowPassword": "demo123",
        "iflowTimeout": 30000
    }

    # Run simulation in a separate thread
    result = await asyncio.to_thread(
        _run_advanced_simulation_sync,
        request=request,
        uid=uid,
        timestamp=timestamp,
        user_settings=user_settings,
        mock_url=mock_url,
        screenshot_storage=screenshot_storage,
        start_date=start_date,
        end_date=end_date,
        spec=spec
    )

    return result
@router.post("/run-advanced-dev", response_model=AdvancedSimulationResult)
async def run_advanced_simulation_dev(
    request: AdvancedSimulationRequest
):
    """
    Development-only endpoint for advanced simulation (no authentication required).
    """
    import os
    from fastapi import HTTPException
    from datetime import datetime, timedelta, timezone
    from zoneinfo import ZoneInfo

    # Only allow in non-production environments
    environment = os.getenv("ENVIRONMENT", "development").lower()
    if environment == "production":
        raise HTTPException(status_code=403, detail="Development endpoint not available in production")

    # Use a fake user for development
    fake_user = {"uid": "dev_test_user", "email": "dev@test.local"}
    uid = fake_user.get("uid")
    timestamp = datetime.utcnow().isoformat().replace(":", "-").replace(".", "-")

    logger.info(f"Starting DEV advanced simulation for user {uid}")

    # Determine simulation period
    duration_days = {
        "1-week": 7,
        "1-month": 30,
        "3-months": 90
    }
    days = duration_days.get(request.duration, 7)

    # Get timezone from spec
    spec = request.spec
    tz_str = spec.get("tz", "Europe/Bucharest")
    tz = ZoneInfo(tz_str)

    # Start from today
    start_date = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=days)

    # Configure mock server
    set_mock_behavior(behavior="success")
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    mock_url = f"{base_url}/mock-iflow/login"

    # Screenshot storage
    screenshot_storage = None
    if request.mode == "screenshot":
        screenshot_storage = get_screenshot_storage()

    # Prepare settings
    user_settings = {
        "iflowUrl": mock_url,
        "iflowUsername": "demo@example.com",
        "iflowPassword": "demo123",
        "iflowHeadless": request.mode != "visual",  # Show browser in visual mode
        "iflowTimeout": 30000
    }

    # Run simulation in a separate thread
    result = await asyncio.to_thread(
        _run_advanced_simulation_sync,
        request=request,
        uid=uid,
        timestamp=timestamp,
        user_settings=user_settings,
        mock_url=mock_url,
        screenshot_storage=screenshot_storage,
        start_date=start_date,
        end_date=end_date,
        spec=spec
    )

    return result
