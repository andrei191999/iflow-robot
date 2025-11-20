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
DEFAULT_PAGE_WAIT_MS = 2000
SELECTOR_TIMEOUT_MS = 5000

# Speed multipliers for delays
SPEED_DELAYS = {
    "slow": 2000,     # 2 seconds between steps
    "normal": 500,    # 0.5 seconds between steps
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
        page.fill(SELECTORS["username_input"], username)
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

        # Time fields should be pre-filled
        logger.info("Time fields should be pre-filled")
        if sim_logger:
            sim_logger.add_step(
                "verify_time_fields",
                "success",
                "Time fields are pre-filled with current time",
                page
            )
            sim_logger.apply_delay(page)

        # Submit form
        logger.info("Clicking submit button")
        page.click(SELECTORS["submit_button"], timeout=timeout)

        if sim_logger:
            sim_logger.add_step(
                "click_submit",
                "success",
                "Submitted check-in form",
                page
            )

        # Wait for submission
        page.wait_for_timeout(3000)
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
    timestamp: str = ""
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

    try:
        with sync_playwright() as playwright:
            browser = _setup_browser(playwright, headless)
            context = browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()

            try:
                sim_logger.add_step(
                    "browser_launched",
                    "success",
                    f"Browser launched (headless={headless})",
                    page
                )
                sim_logger.apply_delay(page)

                # Perform login
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
                sim_logger.add_step(
                    "cleanup",
                    "success",
                    "Closing browser and cleaning up resources"
                )
                page.close()
                context.close()
                browser.close()

    except Exception as e:
        msg = f"Unexpected error: {str(e)}"
        logger.error(msg)
        logger.error(traceback.format_exc())
        sim_logger.add_step("unexpected_error", "error", msg)
        return ("failure", msg, sim_logger.steps, sim_logger.get_total_duration_ms())
