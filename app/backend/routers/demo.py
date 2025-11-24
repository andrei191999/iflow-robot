"""
Demo and simulation endpoints for testing iFlow automation.

Provides endpoints to run simulations with various modes and capture detailed logs.
"""

import asyncio
import logging
from datetime import datetime, timedelta
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
from services.mock_iflow.state import set_mock_behavior
from services.scheduler_math import compute_next_event
from services.holiday_utils import get_holiday_dates, is_holiday, find_next_workday

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
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        mock_url = f"{base_url}/mock-iflow/login"
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
            summary=_generate_summary(status, request.scenario, request.location, duration_ms, len(steps)),
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
    step_count: int
) -> str:
    """Generate human-readable summary of simulation run."""
    location_str = f" at {location}" if location else ""

    if status == "success":
        return (
            f"Successfully completed {scenario}{location_str} in {duration_ms}ms "
            f"({step_count} steps). All automation steps executed correctly."
        )
    else:
        return (
            f"Failed to complete {scenario}{location_str} after {duration_ms}ms "
            f"({step_count} steps executed before failure). Check error details and step logs."
        )


@router.post("/run-public", response_model=PublicSimulationResult)
async def run_public_simulation(request: PublicSimulationRequest):
    """
    Run a public simulation with both check-in and check-out (no auth required).

    This endpoint is designed for public demos and marketing purposes.
    It runs both check-in and check-out operations in sequence using mock credentials.

    **Restrictions:**
    - Always uses mock iFlow server
    - No visual mode (only screenshot or backend)
    - Limited to demo credentials
    - Returns combined results for both operations

    **No authentication required**
    """
    timestamp = datetime.utcnow().isoformat().replace(":", "-").replace(".", "-")
    uid = "public-demo"

    logger.info(
        f"Starting public simulation: mode={request.mode}, speed={request.speed}, "
        f"location={request.location}"
    )

    # Configure mock server for success behavior
    set_mock_behavior(behavior="success")

    # Use mock URL with time parameters
    import os
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    mock_url_base = f"{base_url}/mock-iflow/login"

    # Store times for later use in separate operations
    checkin_time = request.checkInTime
    checkout_time = request.checkOutTime
    logger.info(f"Using mock iFlow with times: checkin={checkin_time}, checkout={checkout_time}")

    # Determine settings based on mode
    # NOTE: Backend simulations ALWAYS run headless (servers have no display)
    # "visual" mode means the user can watch via client-side auto-play in their browser
    capture_screenshots = request.mode in ["screenshot", "visual"]
    headless = True  # Always headless on server

    # Get screenshot storage if needed
    screenshot_storage = None
    if capture_screenshots:
        screenshot_storage = get_screenshot_storage()

    # Prepare demo user settings
    user_settings = {
        "iflowUrl": mock_url_base,
        "iflowUsername": "demo@example.com",
        "iflowPassword": "demo123",
        "iflowHeadless": headless,
        "iflowTimeout": 30000
    }

    total_start_time = datetime.utcnow()

    # Run full simulation sequence (check-in AND check-out) in a single browser session
    try:
        logger.info("Running simulation sequence")

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
            date=datetime.now().strftime("%d/%m/%Y")
        )

        # Unpack results
        checkin_status, checkin_message, checkin_steps, checkin_duration = checkin_result_tuple
        checkout_status, checkout_message, checkout_steps, checkout_duration = checkout_result_tuple

        checkin_result = DemoResult(
            success=(checkin_status == "success"),
            duration_ms=checkin_duration,
            step_count=len(checkin_steps),
            scenario="check-in",
            location=request.location,
            mode=request.mode,
            steps=checkin_steps,
            screenshots=[step.screenshot_url for step in checkin_steps if step.screenshot_url],
            summary=_generate_summary(checkin_status, "check-in", request.location, checkin_duration, len(checkin_steps)),
            error=checkin_message if checkin_status != "success" else None
        )

        checkout_result = DemoResult(
            success=(checkout_status == "success"),
            duration_ms=checkout_duration,
            step_count=len(checkout_steps),
            scenario="check-out",
            location=request.location,
            mode=request.mode,
            steps=checkout_steps,
            screenshots=[step.screenshot_url for step in checkout_steps if step.screenshot_url],
            summary=_generate_summary(checkout_status, "check-out", request.location, checkout_duration, len(checkout_steps)),
            error=checkout_message if checkout_status != "success" else None
        )

    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # Calculate total duration
    total_duration = int((datetime.utcnow() - total_start_time).total_seconds() * 1000)

    # Build combined result
    both_success = checkin_result.success and checkout_result.success
    summary = (
        f"Public demo completed in {total_duration}ms. "
        f"Check-in: {checkin_result.success}, Check-out: {checkout_result.success}. "
        f"Location: {request.location or 'default'}"
    )

    result = PublicSimulationResult(
        success=both_success,
        total_duration_ms=total_duration,
        checkin_result=checkin_result,
        checkout_result=checkout_result,
        summary=summary
    )

    logger.info(f"Public simulation completed: success={both_success}, duration={total_duration}ms")

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
    should_run_live = request.mode in ["screenshot", "visual"]

    # Initialize browser resources - NOT used for live events
    # Each event will get its own browser instance
    playwright = None
    browser = None
    context = None
    page = None


    # Load holiday dates if configured
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
        logger.info(f"Loaded {len(holiday_dates)} holiday dates")

    # Iterate through each day
    current_date = start_date
    run_count = 0
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]



    while current_date < end_date:
        day_of_week = current_date.weekday()
        day_name = day_names[day_of_week]

        # Check if enabled
        day_config = spec.get("week", {}).get(day_name, {})
        is_enabled = day_config.get("enabled", False)

        if is_enabled:
            # Check if current_date is a holiday
            if holidays_config and is_holiday(current_date.date(), holiday_dates):
                behavior = holidays_config.get("behavior", "skip")
                logger.info(f"{current_date.date()} is a holiday, behavior={behavior}")

                if behavior == "skip":
                    # Skip this day entirely
                    skipped_events += 2  # checkIn + checkOut
                    current_date += timedelta(days=1)
                    continue
                elif behavior == "move_to_next_workday":
                    # Move to next workday
                    next_workday = find_next_workday(current_date.date(), holiday_dates)
                    current_date = datetime.combine(next_workday, datetime.min.time()).replace(tzinfo=tz)
                    # Re-evaluate this new date (continue to check if it's enabled)
                    continue
                # elif behavior == "force_checkin": proceed normally (fall through)

            checkin_time_str = day_config.get("checkIn", "09:00")
            checkout_time_str = day_config.get("checkOut", "17:00")
            location = day_config.get("location", "telemunca")

            # Apply jitter
            jitter_config = request.jitter

            # Time Jitter
            checkin_jitter_minutes = 0
            checkout_jitter_minutes = 0
            if jitter_config and jitter_config.time:
                checkin_jitter_minutes = random.randint(-jitter_config.timeRange, jitter_config.timeRange)
                checkout_jitter_minutes = random.randint(-jitter_config.timeRange, jitter_config.timeRange)

            # Execution Jitter
            exec_checkin_jitter_minutes = 0
            exec_checkout_jitter_minutes = 0
            if jitter_config and jitter_config.execution:
                exec_checkin_jitter_minutes = random.randint(-jitter_config.executionRange, jitter_config.executionRange)
                exec_checkout_jitter_minutes = random.randint(-jitter_config.executionRange, jitter_config.executionRange)

            # Calculate times
            checkin_hour, checkin_min = map(int, checkin_time_str.split(":"))
            checkout_hour, checkout_min = map(int, checkout_time_str.split(":"))

            checkin_base = current_date.replace(hour=checkin_hour, minute=checkin_min, second=0, microsecond=0)
            checkout_base = current_date.replace(hour=checkout_hour, minute=checkout_min, second=0, microsecond=0)

            checkin_dt = checkin_base + timedelta(minutes=checkin_jitter_minutes)
            checkout_dt = checkout_base + timedelta(minutes=checkout_jitter_minutes)

            checkin_exec_dt = checkin_dt + timedelta(minutes=exec_checkin_jitter_minutes)
            checkout_exec_dt = checkout_dt + timedelta(minutes=exec_checkout_jitter_minutes)

            checkin_utc = checkin_exec_dt.astimezone(timezone.utc)
            checkout_utc = checkout_exec_dt.astimezone(timezone.utc)

            event_date_local = current_date.strftime("%Y-%m-%d")

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

                    # Collect screenshots
                    for step in checkin_steps:
                        if step.screenshot_url:
                            sample_screenshots.append(step.screenshot_url)
                    for step in checkout_steps:
                        if step.screenshot_url:
                            sample_screenshots.append(step.screenshot_url)

                except Exception as e:
                    logger.error(f"Day simulation failed: {e}")
                    checkin_status = "failure"
                    checkin_message = str(e)
                    checkout_status = "failure"
                    checkout_message = str(e)
            else:
                # Simulated events (not actually run)
                checkin_status = "success"
                checkin_message = None
                checkout_status = "success"
                checkout_message = None

            # Add both events
            events.append(AdvancedSimulationEvent(
                date=event_date_local,
                time=checkin_dt.strftime("%H:%M"),
                event_type="checkIn",
                location=location,
                status=checkin_status,
                reason=checkin_message,
                scheduledAt=checkin_utc.isoformat(),
                localDate=event_date_local
            ))

            events.append(AdvancedSimulationEvent(
                date=event_date_local,
                time=checkout_dt.strftime("%H:%M"),
                event_type="checkOut",
                location=location,
                status=checkout_status,
                reason=checkout_message,
                scheduledAt=checkout_utc.isoformat(),
                localDate=event_date_local
            ))

            run_count += 2  # Increment by 2 since we ran both checkin and checkout

        current_date += timedelta(days=1)

    # Calculate stats
    total_events = len(events)
    success_events = len([e for e in events if e.status == "success"])
    failed_events = len([e for e in events if e.status == "failure"])
    skipped_events = len([e for e in events if e.status == "skipped"])
    success_rate = (success_events / total_events * 100) if total_events > 0 else 0

    return AdvancedSimulationResult(
        success=True,
        total_events=total_events,
        successful_events=success_events,
        failed_events=failed_events,
        skipped_events=skipped_events,
        success_rate=success_rate,
        events=events,
        sample_screenshots=sample_screenshots,
        holiday_handling={"holidaysSkipped": 0, "exceptionsApplied": 0},
        summary=AdvancedSimulationSummary(
            totalEvents=total_events,
            successCount=success_events,
            failureCount=failed_events,
            holidaysSkipped=0,
            dateRange={"start": "", "end": ""}
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
        "iflowHeadless": True,  # Always headless on server (backend mode)
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
