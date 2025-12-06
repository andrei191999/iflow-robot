"""
FastAPI routes for mock iFlow server.

Provides endpoints that mimic app.hriflow.ro behavior and selectors.
"""

import logging
import asyncio
from typing import Optional
from fastapi import APIRouter, Form, Response, Cookie, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from urllib.parse import quote

from .templates import get_login_page, get_dashboard_page, get_success_page
from .state import get_mock_state

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mock-iflow", tags=["Mock iFlow"])


@router.get("/", response_class=HTMLResponse)
async def mock_index():
    """Redirect to login page."""
    return RedirectResponse(url="/mock-iflow/login")


@router.get("/login", response_class=HTMLResponse)
async def mock_login_page(
    event_type: Optional[str] = Query(None, description="Event type (checkIn or checkOut)"),
    checkin: Optional[str] = Query(None, description="Check-in time to preserve"),
    checkout: Optional[str] = Query(None, description="Check-out time to preserve"),
    location: Optional[str] = Query(None, description="Location to preserve"),
    date: Optional[str] = Query(None, description="Date to preserve (dd/mm/yyyy)"),
    auto_run: Optional[str] = Query(None, description="Auto-run bot mode"),
    speed: Optional[str] = Query(None, description="Bot speed (slow/normal/fast)"),
    next_url: Optional[str] = Query(None, description="Next URL to redirect after automation")
):
    """
    Display login page with exact selectors matching real iFlow.

    Query parameters are preserved and passed to dashboard after login.

    Selectors:
    - #td_reg_email (username input)
    - #td_reg_password (password input)
    - button:has-text("Intră în cont") (login button)
    """
    state = get_mock_state()

    # Simulate page load delay
    await asyncio.sleep(state.page_load_delay / 1000.0)

    # Store query params in state if provided (for redirect after login)
    if event_type or checkin or checkout or location or date or auto_run or speed or next_url:
        if not hasattr(state, 'pending_query_params'):
            state.pending_query_params = {}
        state.pending_query_params['latest'] = {
            'event_type': event_type,
            'checkin': checkin,
            'checkout': checkout,
            'location': location,
            'date': date,
            'auto_run': auto_run,
            'speed': speed,
            'next_url': next_url
        }
        logger.info(f"Storing query params for redirect: event_type={event_type}, checkin={checkin}, checkout={checkout}, location={location}, date={date}, auto_run={auto_run}, speed={speed}, next_url={next_url}")

    return HTMLResponse(content=get_login_page())


@router.post("/login")
async def mock_login_submit(
    response: Response,
    username: str = Form(...),
    password: str = Form(...)
):
    """
    Process login form submission.

    Returns dashboard on success, login page with error on failure.
    """
    state = get_mock_state()
    state.login_attempts += 1

    # Simulate login processing delay
    await asyncio.sleep(state.login_delay / 1000.0)

    logger.info(f"Mock login attempt: username={username}")

    # Check behavior mode
    if not state.should_succeed_login():
        logger.info("Mock login configured to fail")
        return HTMLResponse(
            content=get_login_page(error="Invalid credentials - Mock server configured to fail")
        )

    # Validate credentials
    if not state.is_valid_login(username, password):
        logger.info(f"Invalid credentials for user: {username}")
        return HTMLResponse(
            content=get_login_page(error="Invalid email or password")
        )

    # Create session
    session_id = state.create_session()
    logger.info(f"Login successful, session created: {session_id}")

    # Build redirect URL with preserved query params
    redirect_url = "/mock-iflow/dashboard"
    if hasattr(state, 'pending_query_params') and 'latest' in state.pending_query_params:
        params = state.pending_query_params['latest']
        query_parts = []
        if params.get('event_type'):
            query_parts.append(f"event_type={params['event_type']}")
        if params.get('checkin'):
            query_parts.append(f"checkin={params['checkin']}")
        if params.get('checkout'):
            query_parts.append(f"checkout={params['checkout']}")
        if params.get('location'):
            query_parts.append(f"location={params['location']}")
        if params.get('date'):
            query_parts.append(f"date={params['date']}")
        if params.get('auto_run'):
            query_parts.append(f"auto_run={params['auto_run']}")
        if params.get('speed'):
            query_parts.append(f"speed={params['speed']}")
        if params.get('next_url'):
            query_parts.append(f"next_url={quote(params['next_url'])}")
        if query_parts:
            redirect_url += "?" + "&".join(query_parts)
            logger.info(f"Redirecting with query params: {redirect_url}")

    # Set session cookie and redirect to dashboard
    response = RedirectResponse(url=redirect_url, status_code=302)
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        max_age=3600
    )

    return response


@router.get("/dashboard", response_class=HTMLResponse)
async def mock_dashboard(
    session_id: Optional[str] = Cookie(None),
    event_type: Optional[str] = Query(None, description="Event type (checkIn or checkOut)"),
    checkin: Optional[str] = Query(None, description="Pre-fill check-in time (HH:MM)"),
    checkout: Optional[str] = Query(None, description="Pre-fill check-out time (HH:MM)"),
    location: Optional[str] = Query(None, description="Pre-fill location"),
    date: Optional[str] = Query(None, description="Pre-fill date (dd/mm/yyyy)")
):
    """
    Display dashboard with check-in button.

    Requires valid session cookie.

    Query parameters:
    - event_type: Type of event (checkIn or checkOut) - determines which time field to show
    - checkin: Pre-fill check-in time in HH:MM format (e.g., "09:00")
    - checkout: Pre-fill check-out time in HH:MM format (e.g., "17:00")

    Selectors:
    - #app > div.td-router-view > div > div.col-md-12.td-fit-container > div.td-check-in-out > a
      (check-in button)
    """
    state = get_mock_state()

    # Check if logged in
    if not state.is_logged_in(session_id):
        logger.info("Unauthorized dashboard access, redirecting to login")
        return RedirectResponse(url="/mock-iflow/login")

    # Simulate page load delay
    await asyncio.sleep(state.page_load_delay / 1000.0)

    # Check if button should be hidden (no_button behavior)
    if not state.should_show_checkin_button():
        logger.info("Check-in button hidden due to mock behavior")
        # Return dashboard without the button
        html = get_dashboard_page(session_id, event_type=event_type, checkin_time=checkin, checkout_time=checkout, location=location)
        html = html.replace(
            '<a href="#" onclick="openModal(); return false;">Înregistrează Pontaj</a>',
            '<p style="color: #999;">Check-in button not available (mock server configured)</p>'
        )
        return HTMLResponse(content=html)

    return HTMLResponse(content=get_dashboard_page(session_id, event_type=event_type, checkin_time=checkin, checkout_time=checkout, location=location, date=date))


@router.post("/submit")
async def mock_submit_checkin(
    session_id: str = Form(...),
    location: Optional[str] = Form(None),
    checkin_time: Optional[str] = Form(None),
    checkout_time: Optional[str] = Form(None)
):
    """
    Process check-in/check-out form submission.

    Returns JSON response with status and message.
    """
    state = get_mock_state()

    # Check if logged in
    if not state.is_logged_in(session_id):
        logger.info("Unauthorized submit attempt")
        return JSONResponse(
            status_code=401,
            content={"status": "error", "message": "Unauthorized - please log in"}
        )

    # Determine event type based on which time field is filled
    if checkin_time and not checkout_time:
        event_type = "check-in"
        state.checkin_attempts += 1
    elif checkout_time:
        event_type = "check-out"
        state.checkout_attempts += 1
    else:
        event_type = "check-in"
        state.checkin_attempts += 1

    logger.info(f"Mock {event_type} submission: location={location}, time={checkin_time or checkout_time}")

    # Simulate submit processing delay
    await asyncio.sleep(state.submit_delay / 1000.0)

    # Check if submit should fail
    if not state.should_succeed_submit():
        logger.info("Submit configured to fail")
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Submit failed (mock server configured to fail)"}
        )

    # Success
    logger.info(f"Mock {event_type} successful")

    # Determine which time to show in message
    recorded_time = checkout_time if checkout_time else checkin_time

    return JSONResponse(
        content={
            "status": "success",
            "message": f"{event_type.title()} recorded successfully at {recorded_time} ({location or 'No location'})"
        }
    )


@router.get("/stats")
async def mock_stats():
    """Get statistics about mock server usage."""
    state = get_mock_state()

    return {
        "behavior": state.behavior,
        "stats": {
            "login_attempts": state.login_attempts,
            "checkin_attempts": state.checkin_attempts,
            "checkout_attempts": state.checkout_attempts
        },
        "sessions": {
            "active_count": len(state.logged_in_sessions)
        },
        "delays_ms": {
            "page_load": state.page_load_delay,
            "login": state.login_delay,
            "modal_open": state.modal_open_delay,
            "submit": state.submit_delay
        }
    }


@router.post("/reset")
async def mock_reset():
    """Reset mock server state and statistics."""
    from .state import reset_mock_state
    reset_mock_state()
    logger.info("Mock server state reset")
    return {"ok": True, "message": "Mock server reset successful"}


@router.post("/configure")
async def mock_configure(
    behavior: str = Form("success"),
    page_load_delay: Optional[int] = Form(None),
    login_delay: Optional[int] = Form(None),
    modal_open_delay: Optional[int] = Form(None),
    submit_delay: Optional[int] = Form(None)
):
    """
    Configure mock server behavior.

    Args:
        behavior: success, login_fail, timeout, no_button, submit_error
        page_load_delay: Page load delay in ms
        login_delay: Login processing delay in ms
        modal_open_delay: Modal opening delay in ms
        submit_delay: Submit processing delay in ms
    """
    from .state import set_mock_behavior

    set_mock_behavior(
        behavior=behavior,
        page_load_delay=page_load_delay,
        login_delay=login_delay,
        modal_open_delay=modal_open_delay,
        submit_delay=submit_delay
    )

    logger.info(f"Mock server configured: behavior={behavior}")

    return {
        "ok": True,
        "message": f"Mock server configured with behavior: {behavior}"
    }
