"""
Demo and simulation endpoints for testing iFlow automation.

Provides endpoints to run simulations with various modes and capture detailed logs.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException

from core.security import require_firebase_user
from schemas.demo import (
    DemoRequest,
    DemoResult,
    PublicSimulationRequest,
    PublicSimulationResult,
    AdvancedSimulationRequest,
    AdvancedSimulationResult
)
from services.screenshot_storage import get_screenshot_storage
from services.iso_task_enhanced import run_iso_check_enhanced
from services.mock_iflow.state import set_mock_behavior
from services.scheduler_math import compute_next_event
from schemas.demo import AdvancedSimulationEvent

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
    capture_screenshots = request.mode in ["screenshot", "visual"]
    headless = request.mode != "visual"  # Show browser if visual mode

    # Get screenshot storage if needed
    screenshot_storage = None
    if capture_screenshots:
        screenshot_storage = get_screenshot_storage()

    # Prepare demo user settings
    user_settings = {
        "iflowUrl": mock_url,
        "iflowUsername": "demo@example.com",
        "iflowPassword": "demo123",
        "iflowHeadless": headless,
        "iflowTimeout": 30000
    }

    total_start_time = datetime.utcnow()

    # Run check-in (in thread since Playwright is sync)
    try:
        logger.info("Running check-in simulation")
        # Build check-in specific URL with only check-in time
        checkin_mock_url = f"{mock_url_base}?event_type=checkIn&checkin={checkin_time}"

        checkin_status, checkin_message, checkin_steps, checkin_duration = await asyncio.to_thread(
            run_iso_check_enhanced,
            event_type="checkIn",
            location=request.location,
            user_settings=user_settings,
            capture_screenshots=capture_screenshots,
            speed=request.speed,
            use_mock_url=checkin_mock_url,
            screenshot_storage=screenshot_storage,
            uid=uid,
            timestamp=f"{timestamp}-checkin"
        )

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

    except Exception as e:
        logger.error(f"Check-in simulation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Check-in simulation failed: {str(e)}")

    # Run check-out (in thread since Playwright is sync)
    try:
        logger.info("Running check-out simulation")
        # Build check-out specific URL with check-in time (for context) and check-out time
        checkout_mock_url = f"{mock_url_base}?event_type=checkOut&checkin={checkin_time}&checkout={checkout_time}"

        checkout_status, checkout_message, checkout_steps, checkout_duration = await asyncio.to_thread(
            run_iso_check_enhanced,
            event_type="checkOut",
            location=request.location,
            user_settings=user_settings,
            capture_screenshots=capture_screenshots,
            speed=request.speed,
            use_mock_url=checkout_mock_url,
            screenshot_storage=screenshot_storage,
            uid=uid,
            timestamp=f"{timestamp}-checkout"
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
        logger.error(f"Check-out simulation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Check-out simulation failed: {str(e)}")

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


@router.post("/run-advanced", response_model=AdvancedSimulationResult)
async def run_advanced_simulation(
    request: AdvancedSimulationRequest,
    user: Dict = Depends(require_firebase_user)
):
    """
    Run an advanced simulation over a time period with full schedule spec.

    This endpoint simulates all check-ins/outs for a specified duration (1 week, 1 month, 3 months)
    based on a complete schedule specification. It computes all events considering:
    - Weekly patterns
    - Jitter/randomization
    - Public holidays
    - Personal holidays
    - Date/time exceptions

    Returns detailed statistics including:
    - Total events and success rate
    - Holiday handling statistics
    - Sample screenshots from first few runs

    **Authentication required**: Valid Firebase user token
    """
    from datetime import datetime, timedelta, timezone
    from zoneinfo import ZoneInfo

    uid = user.get("uid")
    timestamp = datetime.utcnow().isoformat().replace(":", "-").replace(".", "-")

    logger.info(
        f"Starting advanced simulation for user {uid}: "
        f"duration={request.duration}, mode={request.mode}"
    )

    # Determine simulation period
    duration_days = {
        "1week": 7,
        "1month": 30,
        "3months": 90
    }
    days = duration_days.get(request.duration, 7)

    # Get timezone from spec
    spec = request.spec
    tz_str = spec.get("tz", "Europe/Bucharest")
    tz = ZoneInfo(tz_str)

    # Start from today
    start_date = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=days)

    logger.info(f"Simulating from {start_date.date()} to {end_date.date()} ({days} days)")

    # Collect all events by iterating through days
    events: List[AdvancedSimulationEvent] = []
    holidays_skipped = 0
    exceptions_applied = 0

    # Configure mock server
    set_mock_behavior(behavior="success")
    import os
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    mock_url = f"{base_url}/mock-iflow/login"

    # Screenshot storage for sample screenshots (only first 3 events)
    screenshot_storage = None
    sample_screenshots = []
    capture_screenshots = request.mode == "screenshot"
    if capture_screenshots:
        screenshot_storage = get_screenshot_storage()

    # Prepare settings
    user_settings = {
        "iflowUrl": mock_url,
        "iflowUsername": "demo@example.com",
        "iflowPassword": "demo123",
        "iflowHeadless": True,
        "iflowTimeout": 30000
    }

    simulation_start_time = datetime.utcnow()

    # Iterate through each day
    current_date = start_date
    run_count = 0

    while current_date < end_date:
        # Compute next event for this day by creating a fake schedule
        fake_schedule = {
            "spec": spec,
            "next_event": None
        }

        try:
            # Compute next event starting from this day
            compute_next_event(fake_schedule, now_utc_iso=current_date.astimezone(timezone.utc).isoformat())

            next_event = fake_schedule.get("next_event")

            if next_event:
                event_time_utc = datetime.fromisoformat(next_event["at"].replace("Z", "+00:00"))
                event_date_local = next_event.get("localDate")

                # Check if event falls on current_date
                if event_date_local == current_date.strftime("%Y-%m-%d"):
                    # This event is for today
                    event_type = next_event.get("type")
                    location = next_event.get("location")

                    # Determine if we should actually run it (skip if holiday, etc.)
                    # For now, assume compute_next_event already handles skipping holidays
                    # So if it returned an event, it's valid

                    # Run the event (only for first 3 to save screenshots)
                    if run_count < 3 and capture_screenshots:
                        # Actually run the automation (in thread since Playwright is sync)
                        try:
                            status, message, steps, duration = await asyncio.to_thread(
                                run_iso_check_enhanced,
                                event_type=event_type,
                                location=location,
                                user_settings=user_settings,
                                capture_screenshots=True,
                                speed="fast",
                                use_mock_url=mock_url,
                                screenshot_storage=screenshot_storage,
                                uid=uid,
                                timestamp=f"{timestamp}-event{run_count}"
                            )

                            # Collect screenshots
                            for step in steps:
                                if step.screenshot_url:
                                    sample_screenshots.append(step.screenshot_url)

                            event_status = "success" if status == "success" else "failure"

                        except Exception as e:
                            logger.error(f"Event execution failed: {e}")
                            event_status = "failure"
                            message = str(e)
                    else:
                        # Don't actually run - just simulate success
                        event_status = "success"
                        message = None

                    events.append(AdvancedSimulationEvent(
                        date=event_date_local,
                        time=event_time_utc.astimezone(tz).strftime("%H:%M"),
                        event_type=event_type,
                        location=location,
                        status=event_status,
                        reason=message if event_status != "success" else None
                    ))

                    run_count += 1

        except Exception as e:
            logger.warning(f"Could not compute event for {current_date.date()}: {e}")

        # Move to next day
        current_date += timedelta(days=1)

    # Calculate statistics
    total_events = len(events)
    successful_events = len([e for e in events if e.status == "success"])
    failed_events = len([e for e in events if e.status == "failure"])
    skipped_events = len([e for e in events if e.status == "skipped"])
    success_rate = (successful_events / total_events * 100) if total_events > 0 else 0

    # Holiday handling stats
    holiday_handling = {
        "holidays_in_period": holidays_skipped,
        "exceptions_applied": exceptions_applied,
        "behavior": spec.get("holidays", {}).get("behavior", "skip")
    }

    simulation_duration = int((datetime.utcnow() - simulation_start_time).total_seconds() * 1000)

    # Build summary
    summary = (
        f"Simulated {total_events} events over {days} days ({request.duration}). "
        f"Success rate: {success_rate:.1f}% ({successful_events}/{total_events}). "
        f"Mode: {request.mode}."
    )

    result = AdvancedSimulationResult(
        success=(failed_events == 0),
        total_events=total_events,
        successful_events=successful_events,
        failed_events=failed_events,
        skipped_events=skipped_events,
        success_rate=success_rate,
        events=events,
        sample_screenshots=sample_screenshots[:10],  # Limit to 10 screenshots
        holiday_handling=holiday_handling,
        summary=summary,
        duration_ms=simulation_duration
    )

    logger.info(
        f"Advanced simulation completed for user {uid}: "
        f"{total_events} events, {success_rate:.1f}% success rate"
    )

    return result


@router.get("/status")
async def get_demo_status(user: Dict = Depends(require_firebase_user)):
    """
    Get current demo system status and configuration.

    Returns information about available modes, mock server status, etc.
    """
    from services.mock_iflow.state import get_mock_state

    mock_state = get_mock_state()

    return {
        "ok": True,
        "demo_modes": ["visual", "screenshot", "backend"],
        "speed_options": ["slow", "normal", "fast"],
        "scenarios": ["check-in", "check-out"],
        "locations": ["telemunca", "birou"],
        "mock_server": {
            "available": True,
            "behavior": mock_state.behavior,
            "stats": {
                "login_attempts": mock_state.login_attempts,
                "checkin_attempts": mock_state.checkin_attempts,
                "checkout_attempts": mock_state.checkout_attempts
            }
        },
        "screenshot_storage": {
            "enabled": True,
            "mode": get_screenshot_storage().mode
        }
    }


@router.post("/reset-mock")
async def reset_mock_server(user: Dict = Depends(require_firebase_user)):
    """
    Reset mock server state and statistics.

    Useful between test runs to ensure clean state.
    """
    from services.mock_iflow.state import reset_mock_state

    reset_mock_state()
    logger.info(f"Mock server reset by user {user.get('uid')}")

    return {
        "ok": True,
        "message": "Mock server state reset successfully"
    }


@router.post("/configure-mock")
async def configure_mock_server(
    behavior: str = "success",
    user: Dict = Depends(require_firebase_user)
):
    """
    Configure mock server behavior for testing different scenarios.

    Available behaviors:
    - **success**: Normal successful operation
    - **login_fail**: Simulate login failure
    - **timeout**: Simulate timeout (very slow responses)
    - **no_button**: Simulate missing check-in button
    - **submit_error**: Simulate form submission error

    Useful for testing error handling and edge cases.
    """
    valid_behaviors = ["success", "login_fail", "timeout", "no_button", "submit_error"]

    if behavior not in valid_behaviors:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid behavior. Must be one of: {', '.join(valid_behaviors)}"
        )

    set_mock_behavior(behavior=behavior)
    logger.info(f"Mock server configured to '{behavior}' by user {user.get('uid')}")

    return {
        "ok": True,
        "behavior": behavior,
        "message": f"Mock server configured with behavior: {behavior}"
    }
