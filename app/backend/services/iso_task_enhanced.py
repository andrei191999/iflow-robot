"""
Enhanced iFlow automation with screenshot capture and detailed logging.

This version extends iso_task.py with:
- Step-by-step screenshot capture
- Detailed execution logs with timestamps
- Support for mock iFlow server
- Configurable delays based on speed settings
"""

import os
import logging
import traceback
from typing import Tuple, Optional, Dict, Any, List
from datetime import datetime
from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError

from schemas.demo import SimulationStep

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_PAGE_WAIT_MS = 1000  # Reduced from 2000ms
SELECTOR_TIMEOUT_MS = 5000

# Speed multipliers for delays
SPEED_DELAYS = {
    "slow": 1000,     # 1 second between steps (was 2s)
    "normal": 250,    # 0.25 seconds between steps (was 0.5s)
    "fast": 0         # No artificial delays
}

# Selectors - Matching mock iFlow template
SELECTORS = {
    # Login page selectors
    "username_input": '#td_reg_email',
    "password_input": '#td_reg_password',
    "login_button": 'button[type="submit"]',  # Fixed: was looking for "Intră în cont", now matches type

    # Dashboard - Clock-in button (opens modal)
    "checkin_button": '.td-check-in-out-button',  # Simplified: use class instead of complex path

    # Check-in/out modal selectors
    "modal_body": '.td-checkin-modal .modal-body',
    "location_selector": '.td-select-single-button',  # Simplified: use class instead of complex path
    "checkin_time_field": '#td-ckeck-in-out-start-time-65',  # Clock IN time
    "checkout_time_field": '#td-ckeck-in-out-end-time-65',  # Clock OUT time
    "submit_button": '.modal-default-button',  # Simplified: use class instead of complex path
}


class SimulationLogger:
    """Captures detailed logs and screenshots for simulation runs."""

    def __init__(
        self,
        capture_screenshots: bool = False,
        speed: str = "normal",
        screenshot_storage = None,
        uid: str = "",
        timestamp: str = ""
    ):
        self.capture_screenshots = capture_screenshots
        self.speed = speed
        self.delay_ms = SPEED_DELAYS.get(speed, 500)
        self.screenshot_storage = screenshot_storage
        self.uid = uid
        self.timestamp = timestamp
        self.steps: List[SimulationStep] = []
        self.current_step = 0
        self.start_time = datetime.utcnow()

    def add_step(
        self,
        name: str,
        status: str = "success",
        message: str = "",
        page: Optional[Page] = None
    ) -> SimulationStep:
        """
        Add a step to the simulation log.

        Args:
            name: Human-readable step name
            status: success, warning, or error
            message: Detailed message
            page: Playwright page for screenshot capture

        Returns:
            The created SimulationStep
        """
        step_start = datetime.utcnow()
        screenshot_url = None

        # Capture screenshot if enabled
        if self.capture_screenshots and page and self.screenshot_storage:
            try:
                screenshot_bytes = page.screenshot(type='png', full_page=False)
                screenshot_url = self.screenshot_storage.save_screenshot(
                    uid=self.uid,
                    timestamp=self.timestamp,
                    step_number=self.current_step,
                    screenshot_data=screenshot_bytes,
                    step_name=name
                )
                logger.debug(f"Screenshot captured for step {self.current_step}: {name}")
            except Exception as e:
                logger.warning(f"Failed to capture screenshot for step {name}: {e}")

        step_end = datetime.utcnow()
        duration_ms = int((step_end - step_start).total_seconds() * 1000)

        step = SimulationStep(
            step_number=self.current_step,
            name=name,
            timestamp=step_start.isoformat() + "Z",
            duration_ms=duration_ms,
            status=status,
            message=message,
            screenshot_url=screenshot_url
        )

        self.steps.append(step)
        self.current_step += 1

        logger.info(f"Step {step.step_number}: {name} - {status} - {message}")

        return step

    def apply_delay(self, page: Optional[Page] = None):
        """Apply speed-based delay between steps."""
        if self.delay_ms > 0 and page:
            page.wait_for_timeout(self.delay_ms)

    def get_total_duration_ms(self) -> int:
        """Get total duration since start."""
        return int((datetime.utcnow() - self.start_time).total_seconds() * 1000)

    def get_all_screenshots(self) -> List[str]:
        """Get list of all screenshot URLs."""
        return [step.screenshot_url for step in self.steps if step.screenshot_url]


def _setup_browser(playwright, headless: bool = True) -> Browser:
    """Initialize browser with appropriate settings."""
    logger.info(f"Launching browser (headless={headless})")
    return playwright.chromium.launch(
        headless=headless,
        args=['--disable-blink-features=AutomationControlled']
    )


def _inject_cursor(page: Page):
    """Inject a visual cursor (red dot) into the page for easier tracking."""
    try:
        page.evaluate("""
            () => {
                if (document.getElementById('automation-cursor')) return;

                const cursor = document.createElement('div');
                cursor.id = 'automation-cursor';
                cursor.style.position = 'fixed';
                cursor.style.width = '20px';
                cursor.style.height = '20px';
                cursor.style.borderRadius = '50%';
                cursor.style.backgroundColor = 'rgba(255, 0, 0, 0.8)';
                cursor.style.border = '2px solid rgba(255, 255, 255, 0.9)';
                cursor.style.boxShadow = '0 0 10px rgba(255, 0, 0, 0.8)';
                cursor.style.zIndex = '999999';
                cursor.style.pointerEvents = 'none';
                cursor.style.transition = 'all 0.3s ease-out';
                cursor.style.display = 'none';
                document.body.appendChild(cursor);
            }
        """)
        logger.debug("Visual cursor injected")
    except Exception as e:
        logger.warning(f"Failed to inject visual cursor: {e}")


def _move_cursor_to_element(page: Page, selector: str, timeout: int = 5000):
    """Move the visual cursor to an element before interacting with it."""
    try:
        # First ensure element exists
        page.wait_for_selector(selector, timeout=timeout)

        # Move cursor to element
        page.evaluate(f"""
            (selector) => {{
                const cursor = document.getElementById('automation-cursor');
                if (!cursor) return;

                const element = document.querySelector(selector);
                if (!element) return;

                const rect = element.getBoundingClientRect();
                const x = rect.left + rect.width / 2;
                const y = rect.top + rect.height / 2;

                cursor.style.display = 'block';
                cursor.style.left = x - 10 + 'px';
                cursor.style.top = y - 10 + 'px';
            }}
        """, selector)

        # Small delay to see the cursor movement
        page.wait_for_timeout(200)
        logger.debug(f"Moved cursor to: {selector}")
    except Exception as e:
        logger.warning(f"Failed to move cursor to {selector}: {e}")



def _login(
    page: Page,
    url: str,
    username: str,
    password: str,
    timeout: int,
    sim_logger: Optional[SimulationLogger] = None
) -> bool:
    """
    Perform login to iFlow system with enhanced logging.

    Returns True if login successful, False otherwise.
    """
    try:
        if sim_logger:
            sim_logger.add_step(
                "navigate_to_login",
                "success",
                f"Navigating to {url}",
                page
            )

        logger.info(f"Navigating to {url}")
        page.goto(url, timeout=timeout)

        # Inject visual cursor
        _inject_cursor(page)

        if sim_logger:
            sim_logger.apply_delay(page)

        # Wait for page to stabilize
        page.wait_for_timeout(DEFAULT_PAGE_WAIT_MS)

        # Check if already logged in
        try:
            page.wait_for_selector(SELECTORS["username_input"], timeout=SELECTOR_TIMEOUT_MS)
            logger.info("Login form detected")

            if sim_logger:
                sim_logger.add_step(
                    "login_form_detected",
                    "success",
                    "Login form found on page",
                    page
                )

        except PlaywrightTimeoutError:
            if "login" not in page.url.lower() and "signin" not in page.url.lower():
                logger.info("Already logged in")
                if sim_logger:
                    sim_logger.add_step(
                        "already_logged_in",
                        "success",
                        "Already authenticated, no login needed",
                        page
                    )
                return True

        # Fill credentials
        logger.info(f"Filling in username: {username}")
        _move_cursor_to_element(page, SELECTORS["username_input"])
        page.fill(SELECTORS["username_input"], username)
        _move_cursor_to_element(page, SELECTORS["password_input"])
        page.fill(SELECTORS["password_input"], password)

        if sim_logger:
            sim_logger.add_step(
                "fill_credentials",
                "success",
                f"Entered username: {username}",
                page
            )
            sim_logger.apply_delay(page)

        # Click login button and wait for navigation
        logger.info("Clicking login button")

        # Use Promise.all pattern to wait for navigation after click
        try:
            # Wait for either navigation or URL change
            _move_cursor_to_element(page, SELECTORS["login_button"])
            page.click(SELECTORS["login_button"])

            if sim_logger:
                sim_logger.add_step(
                    "click_login_button",
                    "success",
                    "Submitted login form",
                    page
                )

            # Wait for navigation to complete - try multiple strategies
            logger.info("Waiting for navigation after login")

            # First wait for network to settle
            try:
                page.wait_for_load_state("networkidle", timeout=timeout)
            except Exception:
                # If networkidle fails, try waiting for load state
                page.wait_for_load_state("load", timeout=5000)

            # Give extra time for any redirects to complete
            page.wait_for_timeout(2000)

        except Exception as e:
            logger.warning(f"Navigation wait exception: {e}")
            # Continue anyway - check URL to see if login succeeded

        if sim_logger:
            sim_logger.apply_delay(page)
            sim_logger.add_step(
                "login_complete",
                "success",
                f"Login navigation complete, current URL: {page.url}",
                page
            )

        # Verify login success - check if we're NOT on login page anymore
        current_url = page.url.lower()
        logger.info(f"Post-login URL check: {current_url}")

        if "login" in current_url or "signin" in current_url:
            logger.error("Login failed - still on login page")
            if sim_logger:
                sim_logger.add_step(
                    "login_failed",
                    "error",
                    "Login failed - still on login page",
                    page
                )
            return False

        # Also check for "dashboard" or redirected path as positive signal
        if "dashboard" in current_url or current_url.endswith("/mock-iflow/dashboard"):
            logger.info("Login successful - redirected to dashboard")
            return True

        logger.info("Login successful")
        return True

    except PlaywrightTimeoutError as e:
        logger.error(f"Timeout during login: {str(e)}")
        if sim_logger:
            sim_logger.add_step(
                "login_timeout",
                "error",
                f"Login timed out: {str(e)}",
                page
            )
        return False
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        if sim_logger:
            sim_logger.add_step(
                "login_error",
                "error",
                f"Login error: {str(e)}",
                page
            )
        return False


def _perform_checkin(
    page: Page,
    location: Optional[str],
    timeout: int,
    sim_logger: Optional[SimulationLogger] = None
) -> Tuple[str, str]:
    """
    Perform check-in action with enhanced logging.

    Returns (status, message) tuple.
    """
    try:
        logger.info(f"Starting check-in procedure at location={location}")

        # Re-inject cursor on dashboard page (lost after navigation from login)
        _inject_cursor(page)

        if sim_logger:
            sim_logger.add_step(
                "view_dashboard",
                "success",
                "Viewing dashboard page",
                page
            )
            sim_logger.apply_delay(page)

        # Click check-in button to open modal
        logger.info("Looking for check-in/out button")
        try:
            page.wait_for_selector(SELECTORS["checkin_button"], timeout=timeout)
            _move_cursor_to_element(page, SELECTORS["checkin_button"])
            page.click(SELECTORS["checkin_button"], timeout=SELECTOR_TIMEOUT_MS)
            logger.info("Check-in button clicked")

            if sim_logger:
                sim_logger.add_step(
                    "click_checkin_button",
                    "success",
                    "Opened check-in/out modal",
                    page
                )
                sim_logger.apply_delay(page)

        except Exception as e:
            logger.error(f"Could not click check-in button: {e}")
            if sim_logger:
                sim_logger.add_step(
                    "checkin_button_error",
                    "error",
                    f"Failed to click check-in button: {e}",
                    page
                )
            return ("failure", f"Could not click check-in button: {e}")

        # Wait for modal
        logger.info("Waiting for modal to appear")
        page.wait_for_selector(SELECTORS["modal_body"], timeout=timeout)
        page.wait_for_timeout(DEFAULT_PAGE_WAIT_MS)

        if sim_logger:
            sim_logger.add_step(
                "modal_opened",
                "success",
                "Check-in/out modal is now visible",
                page
            )
            sim_logger.apply_delay(page)

        # Select location if provided
        if location:
            try:
                logger.info(f"Selecting location: {location}")
                _move_cursor_to_element(page, SELECTORS["location_selector"])
                page.click(SELECTORS["location_selector"], timeout=SELECTOR_TIMEOUT_MS)
                page.wait_for_timeout(1000)

                # Try to find and click the location option
                if location.lower() == "telemunca":
                    location_options = [
                        'text="Telemunca"',
                        ':has-text("Telemunca")',
                    ]
                elif location.lower() == "birou":
                    location_options = [
                        'text="Birou"',
                        ':has-text("Birou")',
                    ]
                else:
                    location_options = [f'text="{location}"']

                location_selected = False
                for loc_selector in location_options:
                    try:
                        _move_cursor_to_element(page, loc_selector, timeout=1000)
                        page.click(loc_selector, timeout=2000)
                        logger.info(f"Selected location: {location}")
                        location_selected = True
                        break
                    except Exception:
                        continue

                if sim_logger:
                    if location_selected:
                        sim_logger.add_step(
                            "select_location",
                            "success",
                            f"Selected location: {location}",
                            page
                        )
                    else:
                        sim_logger.add_step(
                            "select_location",
                            "warning",
                            f"Could not select location '{location}', proceeding anyway",
                            page
                        )
                    sim_logger.apply_delay(page)

            except Exception as e:
                logger.warning(f"Error selecting location: {e}")
                if sim_logger:
                    sim_logger.add_step(
                        "location_error",
                        "warning",
                        f"Location selection failed: {e}, continuing",
                        page
                    )

        # Extract times from URL to know what to fill
        from urllib.parse import urlparse, parse_qs
        current_url = page.url
        parsed = urlparse(current_url)
        query_params = parse_qs(parsed.query)

        checkin_time = query_params.get('checkin', ['09:00'])[0]
        checkout_time = query_params.get('checkout', ['17:00'])[0]
        event_type = query_params.get('event_type', ['checkIn'])[0]

        logger.info(f"Filling time fields: event_type={event_type}, checkin={checkin_time}, checkout={checkout_time}")

        # Fill check-in time field (ONLY for check-in event)
        if event_type == "checkIn":
            try:
                _move_cursor_to_element(page, SELECTORS["checkin_time_field"])
                page.wait_for_timeout(300)
                page.click(SELECTORS["checkin_time_field"])
                page.wait_for_timeout(200)
                # Clear any existing value
                page.fill(SELECTORS["checkin_time_field"], "")
                # Type the time
                page.fill(SELECTORS["checkin_time_field"], checkin_time)
                logger.info(f"Filled check-in time: {checkin_time}")
            except Exception as e:
                logger.warning(f"Failed to fill check-in time: {e}")

        # Fill check-out time field (ONLY for check-out event)
        if event_type == "checkOut":
            try:
                _move_cursor_to_element(page, SELECTORS["checkout_time_field"])
                page.wait_for_timeout(300)
                page.click(SELECTORS["checkout_time_field"])
                page.wait_for_timeout(200)
                # Clear any existing value
                page.fill(SELECTORS["checkout_time_field"], "")
                # Type the time
                page.fill(SELECTORS["checkout_time_field"], checkout_time)
                logger.info(f"Filled check-out time: {checkout_time}")
            except Exception as e:
                logger.warning(f"Failed to fill check-out time: {e}")

        if sim_logger:
            sim_logger.add_step(
                "fill_time_fields",
                "success",
                f"Filled time fields: check-in={checkin_time}, check-out={checkout_time}",
                page
            )
            sim_logger.apply_delay(page)

        # Submit form
        logger.info("Clicking submit button")
        _move_cursor_to_element(page, SELECTORS["submit_button"])
        page.click(SELECTORS["submit_button"], timeout=timeout)

        if sim_logger:
            sim_logger.add_step(
                "click_submit",
                "success",
                "Submitted check-in form",
                page
            )

        # Wait for submission
        page.wait_for_timeout(2000)  # Wait for submission to complete (reduced from 3000ms)
        page.wait_for_load_state("networkidle", timeout=timeout)

        if sim_logger:
            sim_logger.apply_delay(page)
            sim_logger.add_step(
                "submission_complete",
                "success",
                "Form submission processed",
                page
            )

        # Verify success
        content = page.content().lower()
        if "success" in content or "pontaj inregistrat" in content or "successfully" in content:
            msg = f"Check-in successful at location={location}"
            logger.info(msg)
            if sim_logger:
                sim_logger.add_step(
                    "verify_success",
                    "success",
                    "Success message detected on page",
                    page
                )
            return ("success", msg)
        elif "error" in content or "eroare" in content:
            msg = "Check-in failed - error detected"
            logger.error(msg)
            if sim_logger:
                sim_logger.add_step(
                    "verify_error",
                    "error",
                    "Error message detected on page",
                    page
                )
            return ("failure", msg)
        else:
            # Assume success if modal closed
            try:
                if page.is_visible(SELECTORS["modal_body"], timeout=DEFAULT_PAGE_WAIT_MS):
                    msg = "Check-in may have failed - modal still visible"
                    logger.warning(msg)
                    return ("failure", msg)
            except:
                pass

            msg = f"Check-in completed at location={location}"
            logger.info(msg)

            # If we're on success page, navigate back to dashboard for next event
            if "success" in page.url.lower() or "/submit" in page.url.lower():
                logger.info("Navigating back to dashboard for next event")
                dashboard_url = page.url.split("?")[0].replace("/submit", "/dashboard")
                page.goto(dashboard_url, timeout=timeout)
                page.wait_for_timeout(1000)
                if sim_logger:
                    sim_logger.add_step(
                        "navigate_to_dashboard",
                        "success",
                        "Returned to dashboard for next event",
                        page
                    )

            return ("success", msg)

    except PlaywrightTimeoutError:
        msg = f"Timeout during check-in at location={location}"
        logger.error(msg)
        if sim_logger:
            sim_logger.add_step(
                "checkin_timeout",
                "error",
                "Check-in operation timed out",
                page
            )
        return ("failure", msg)
    except Exception as e:
        msg = f"Error during check-in: {str(e)}"
        logger.error(msg)
        if sim_logger:
            sim_logger.add_step(
                "checkin_error",
                "error",
                f"Check-in failed: {str(e)}",
                page
            )
        return ("failure", msg)


def run_simulation_sequence(
    location: str,
    checkin_time: str,
    checkout_time: str,
    user_settings: Dict[str, Any],
    capture_screenshots: bool,
    speed: str,
    mock_url_base: str,
    screenshot_storage,
    uid: str,
    timestamp: str,
    date: Optional[str] = None
) -> Tuple[Any, Any]:
    """
    Run both check-in and check-out in a single browser session.
    """
    checkin_result = None
    checkout_result = None

    headless = user_settings.get("iflowHeadless", True)

    try:
        with sync_playwright() as playwright:
            # 1. Launch browser once
            browser = _setup_browser(playwright, headless)
            context = browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()

            # Inject cursor immediately
            _inject_cursor(page)

            # 2. Run Check-in
            checkin_params = f"event_type=checkIn&checkin={checkin_time}&location={location}"
            if date:
                checkin_params += f"&date={date}"
            checkin_mock_url = f"{mock_url_base}?{checkin_params}"

            checkin_result = run_iso_check_enhanced(
                event_type="checkIn",
                location=location,
                user_settings=user_settings,
                capture_screenshots=capture_screenshots,
                speed=speed,
                use_mock_url=checkin_mock_url,
                screenshot_storage=screenshot_storage,
                uid=uid,
                timestamp=f"{timestamp}-checkin",
                existing_page=page,
                close_browser_on_exit=False
            )

            # Small pause between operations
            page.wait_for_timeout(1000)  # Reduced from 2000ms

            # 3. Run Check-out
            checkout_params = f"event_type=checkOut&checkin={checkin_time}&checkout={checkout_time}&location={location}"
            if date:
                checkout_params += f"&date={date}"
            checkout_mock_url = f"{mock_url_base}?{checkout_params}"

            checkout_result = run_iso_check_enhanced(
                event_type="checkOut",
                location=location,
                user_settings=user_settings,
                capture_screenshots=capture_screenshots,
                speed=speed,
                use_mock_url=checkout_mock_url,
                screenshot_storage=screenshot_storage,
                uid=uid,
                timestamp=f"{timestamp}-checkout",
                existing_page=page,
                close_browser_on_exit=False
            )

            # Cleanup handled by context manager
            page.close()
            context.close()
            browser.close()

    except Exception as e:
        logger.error(f"Error in simulation sequence: {e}")
        # If we failed before getting results, create failure results
        if not checkin_result:
            checkin_result = ("failure", f"Sequence error: {e}", [], 0)
        if not checkout_result:
            checkout_result = ("failure", f"Sequence error: {e}", [], 0)

    return checkin_result, checkout_result


def _perform_checkout(
    page: Page,
    location: Optional[str],
    timeout: int,
    sim_logger: Optional[SimulationLogger] = None
) -> Tuple[str, str]:
    """Perform check-out action (same as check-in on this system)."""
    logger.info("Check-out uses same flow as check-in")
    return _perform_checkin(page, location, timeout, sim_logger)


def run_iso_check_enhanced(
    event_type: str,
    location: Optional[str],
    user_settings: Optional[Dict[str, Any]] = None,
    capture_screenshots: bool = False,
    speed: str = "normal",
    use_mock_url: Optional[str] = None,
    screenshot_storage = None,
    uid: str = "",
    timestamp: str = "",
    existing_page: Optional[Page] = None,
    close_browser_on_exit: bool = True
) -> Tuple[str, str, List[SimulationStep], int]:
    """
    Execute iFlow check-in/out with enhanced logging and screenshots.

    Args:
        event_type: "checkIn" or "checkOut"
        location: Optional location ("telemunca" or "birou")
        user_settings: User settings dict from Firestore
        capture_screenshots: Whether to capture screenshots at each step
        speed: "slow", "normal", or "fast" for delay timing
        use_mock_url: Override URL with mock server (e.g., "http://localhost:8000/mock-iflow")
        screenshot_storage: ScreenshotStorage instance for saving screenshots
        uid: User ID for screenshot path
        timestamp: Timestamp for screenshot path
        existing_page: Optional existing Playwright page to reuse
        close_browser_on_exit: Whether to close the browser after execution

    Returns:
        Tuple of (status, message, steps, duration_ms)
    """
    logger.info(f"=== Enhanced iFlow automation: {event_type} at location={location} ===")

    # Initialize simulation logger
    sim_logger = SimulationLogger(
        capture_screenshots=capture_screenshots,
        speed=speed,
        screenshot_storage=screenshot_storage,
        uid=uid,
        timestamp=timestamp
    )

    # Get configuration
    if user_settings:
        url = user_settings.get("iflowUrl", "https://app.hriflow.ro/#/dashboard")
        username = user_settings.get("iflowUsername", "")
        password = user_settings.get("iflowPassword", "")
        headless = user_settings.get("iflowHeadless", True)
        timeout = user_settings.get("iflowTimeout", 30000)
    else:
        url = os.getenv("IFLOW_URL", "https://app.hriflow.ro/#/dashboard")
        username = os.getenv("IFLOW_USERNAME", "")
        password = os.getenv("IFLOW_PASSWORD", "")
        headless = os.getenv("IFLOW_HEADLESS", "true").lower() == "true"
        timeout = int(os.getenv("IFLOW_TIMEOUT", "30000"))

    # Override with mock URL if provided
    if use_mock_url:
        url = use_mock_url
        logger.info(f"Using mock iFlow server at: {url}")

    # Override headless based on capture mode
    if capture_screenshots or speed == "slow":
        # For screenshot/visual modes, might want to see browser
        pass

    logger.info(f"Configuration: url={url}, username={username}, headless={headless}, timeout={timeout}ms")

    # Validate configuration
    if not username or not password:
        msg = "iFlow credentials not configured"
        logger.error(msg)
        sim_logger.add_step("validate_config", "error", msg)
        return ("failure", msg, sim_logger.steps, sim_logger.get_total_duration_ms())

    if not event_type:
        msg = "Event type not specified"
        logger.error(msg)
        sim_logger.add_step("validate_config", "error", msg)
        return ("failure", msg, sim_logger.steps, sim_logger.get_total_duration_ms())

    event_type_lower = event_type.lower()
    if event_type_lower not in ["checkin", "checkout"]:
        msg = f"Unknown event type: {event_type}"
        logger.error(msg)
        sim_logger.add_step("validate_config", "error", msg)
        return ("failure", msg, sim_logger.steps, sim_logger.get_total_duration_ms())

    sim_logger.add_step(
        "validate_config",
        "success",
        f"Configuration validated: {event_type} at {location or 'default location'}"
    )

    browser = None
    context = None
    page = None
    playwright = None

    try:
        if existing_page:
            logger.info("Using existing browser page")
            page = existing_page
            # We don't manage the lifecycle of existing page
        else:
            playwright = sync_playwright().start()
            browser = _setup_browser(playwright, headless)
            context = browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()

            sim_logger.add_step(
                "browser_launched",
                "success",
                f"Browser launched (headless={headless})",
                page
            )
            sim_logger.apply_delay(page)

        try:
            # Perform login
            # If reusing page, check if we're already on dashboard
            if existing_page:
                current_url = page.url.lower()
                if "dashboard" in current_url:
                    logger.info("Reusing existing page already on dashboard, skipping login")
                    # Navigate to dashboard with new query parameters
                    dashboard_url = url.replace("/login", "/dashboard")
                    logger.info(f"Navigating to dashboard with new params: {dashboard_url}")
                    page.goto(dashboard_url, timeout=timeout)
                    page.wait_for_timeout(1000)
                    if sim_logger:
                        sim_logger.add_step(
                            "navigate_dashboard",
                            "success",
                            f"Navigated to dashboard with new parameters",
                            page
                        )
                else:
                    # Need to login
                    if not _login(page, url, username, password, timeout, sim_logger):
                        return (
                            "failure",
                            "Login failed - check credentials",
                            sim_logger.steps,
                            sim_logger.get_total_duration_ms()
                        )
            else:
                # New page, always login
                if not _login(page, url, username, password, timeout, sim_logger):
                    return (
                        "failure",
                        "Login failed - check credentials",
                        sim_logger.steps,
                        sim_logger.get_total_duration_ms()
                    )

            # Perform action
            if event_type_lower == "checkin":
                status, message = _perform_checkin(page, location, timeout, sim_logger)
            else:
                status, message = _perform_checkout(page, location, timeout, sim_logger)

            duration_ms = sim_logger.get_total_duration_ms()
            logger.info(f"=== Enhanced automation completed: {status} - {message} ({duration_ms}ms) ===")

            return (status, message, sim_logger.steps, duration_ms)

        finally:
            if close_browser_on_exit and not existing_page:
                sim_logger.add_step(
                    "cleanup",
                    "success",
                    "Closing browser and cleaning up resources"
                )
                if page: page.close()
                if context: context.close()
                if browser: browser.close()
                if playwright: playwright.stop()
            elif not close_browser_on_exit:
                logger.info("Keeping browser open for next step")

    except Exception as e:
        msg = f"Unexpected error: {str(e)}"
        logger.error(msg)
        logger.error(traceback.format_exc())
        sim_logger.add_step("unexpected_error", "error", msg)
        return ("failure", msg, sim_logger.steps, sim_logger.get_total_duration_ms())
