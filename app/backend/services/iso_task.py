import os
import logging
import traceback
from typing import Tuple, Optional, Dict, Any
from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_PAGE_WAIT_MS = 2000
SELECTOR_TIMEOUT_MS = 5000

# Selectors - VERIFIED for app.hriflow.ro (updated from selectors.txt)
SELECTORS = {
    # Login page selectors
    "username_input": '#td_reg_email',
    "password_input": '#td_reg_password',
    # Use text-based selector to avoid clicking "Sign in with Google" button
    "login_button": 'button:has-text("Intră în cont")',

    # Dashboard - Clock-in button (opens modal) - UPDATED!
    "checkin_button": '#app > div.td-router-view > div > div.col-md-12.td-fit-container > div.td-check-in-out > a',

    # Check-in/out modal selectors
    "modal_body": '.td-checkin-modal .modal-body',
    "location_selector": '#app > div.td-router-view > div > div.col-md-12.td-fit-container > div.td-check-in-out > div.td-checkin-modal > div > div > div > div.modal-body > div > form > div:nth-child(2) > div > div > div > div > div.td-select-single-button',
    "checkin_time_field": '#td-ckeck-in-out-end-time-67',  # Note: typo in their ID (ckeck)
    "checkout_time_field": '#td-ckeck-in-out-start-time-67',
    "submit_button": '#app > div.td-router-view > div > div.col-md-12.td-fit-container > div.td-check-in-out > div.td-checkin-modal > div > div > div > div.modal-footer > button',
}


def _setup_browser(playwright, headless: bool = True) -> Browser:
    """Initialize browser with appropriate settings."""
    logger.info(f"Launching browser (headless={headless})")
    return playwright.chromium.launch(
        headless=headless,
        args=['--disable-blink-features=AutomationControlled']
    )


def _login(page: Page, url: str, username: str, password: str, timeout: int) -> bool:
    """
    Perform login to iFlow system.
    Returns True if login successful, False otherwise.
    """
    try:
        logger.info(f"Navigating to {url}")
        page.goto(url, timeout=timeout)
        logger.debug(f"Page loaded: {page.url}")

        # Wait a bit for any redirects
        page.wait_for_timeout(DEFAULT_PAGE_WAIT_MS)
        logger.debug(f"Current URL after wait: {page.url}")

        # Check if we're already logged in (no login form visible)
        try:
            page.wait_for_selector(SELECTORS["username_input"], timeout=SELECTOR_TIMEOUT_MS)
            logger.info("Login form detected, proceeding with authentication")
        except PlaywrightTimeoutError:
            logger.info("No login form detected - may already be logged in or different page structure")
            # Check if we're on a dashboard or main page
            if "login" not in page.url.lower() and "signin" not in page.url.lower():
                logger.info("Appears to be logged in already")
                return True

        # Fill in credentials
        logger.info(f"Filling in username: {username}")
        page.fill(SELECTORS["username_input"], username)
        page.fill(SELECTORS["password_input"], password)
        logger.debug("Password filled (hidden)")

        # Take a screenshot before clicking login (for debugging)
        try:
            screenshot_path = "login_before.png"
            page.screenshot(path=screenshot_path)
            logger.debug(f"Screenshot saved: {screenshot_path}")
        except Exception as e:
            logger.warning(f"Could not save screenshot: {e}")

        # Click login button and wait for navigation
        logger.info("Clicking login button")
        page.click(SELECTORS["login_button"])

        # Wait for navigation to complete - try multiple strategies
        logger.info("Waiting for navigation after login")
        try:
            page.wait_for_load_state("networkidle", timeout=timeout)
        except Exception:
            # If networkidle fails, try waiting for load state
            try:
                page.wait_for_load_state("load", timeout=5000)
            except Exception:
                pass

        # Give extra time for any redirects to complete
        page.wait_for_timeout(2000)

        # Take a screenshot after login (for debugging)
        try:
            screenshot_path = "login_after.png"
            page.screenshot(path=screenshot_path)
            logger.debug(f"Screenshot saved: {screenshot_path}")
        except Exception as e:
            logger.warning(f"Could not save screenshot: {e}")

        # Check if login was successful
        current_url = page.url.lower()
        logger.debug(f"Post-login URL: {current_url}")

        if "login" in current_url or "signin" in current_url:
            logger.error("Login appears to have failed - still on login page")
            # Check for error messages
            content = page.content().lower()
            if "error" in content or "invalid" in content or "incorrect" in content:
                logger.error("Error message detected on page")
            return False

        # Also check for "dashboard" as positive signal
        if "dashboard" in current_url:
            logger.info("Login successful - redirected to dashboard")
            return True

        # Check page content for error indicators
        content = page.content().lower()
        if "invalid credentials" in content or "wrong password" in content:
            logger.error("Invalid credentials message detected")
            return False

        logger.info("Login successful")
        return True

    except PlaywrightTimeoutError as e:
        logger.error(f"Timeout during login: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        logger.debug(traceback.format_exc())
        return False


def _select_location(page: Page, location: Optional[str]) -> bool:
    """
    Select work location if required (telemunca or birou).
    Returns True if successful or not needed, False on error.
    """
    if not location:
        logger.debug("No location specified, skipping location selection")
        return True

    try:
        location_lower = location.lower()
        logger.info(f"Attempting to select location: {location_lower}")

        if location_lower == "telemunca":
            selector = SELECTORS["location_telemunca"]
            if page.is_visible(selector, timeout=SELECTOR_TIMEOUT_MS):
                page.click(selector)
                logger.info("Selected location: telemunca")
            else:
                logger.warning("Telemunca selector not visible, may not be required")
        elif location_lower == "birou":
            selector = SELECTORS["location_birou"]
            if page.is_visible(selector, timeout=SELECTOR_TIMEOUT_MS):
                page.click(selector)
                logger.info("Selected location: birou")
            else:
                logger.warning("Birou selector not visible, may not be required")

        return True

    except Exception as e:
        logger.warning(f"Could not select location {location}: {str(e)}")
        # Don't fail the whole operation if location selection fails
        return True


def _perform_checkin(page: Page, location: Optional[str], timeout: int) -> Tuple[str, str]:
    """
    Perform check-in action on app.hriflow.ro

    The flow is:
    1. Click button to open check-in/out modal
    2. Modal appears with location selector and time fields
    3. Select location (if provided)
    4. Times should be pre-filled with current time
    5. Click submit button

    Returns (status, message) tuple.
    """
    try:
        logger.info(f"Starting check-in procedure at location={location}")

        # Take screenshot of dashboard
        try:
            page.screenshot(path="checkin_dashboard.png")
            logger.debug("Screenshot saved: checkin_dashboard.png")
        except Exception:
            pass

        # Look for the check-in button on the main page
        logger.info("Looking for check-in/out button to open modal")
        try:
            # Wait for check-in button - this opens the modal
            page.wait_for_selector(SELECTORS["checkin_button"], timeout=timeout)
            page.click(SELECTORS["checkin_button"], timeout=SELECTOR_TIMEOUT_MS)
            logger.info("Check-in button clicked, modal should open")
        except Exception as e:
            logger.warning(f"Could not click check-in button: {e}. Trying alternative approach...")
            # The modal might already be open
            pass

        # Wait for modal to appear
        logger.info("Waiting for check-in/out modal to appear")
        page.wait_for_selector(SELECTORS["modal_body"], timeout=timeout)
        page.wait_for_timeout(DEFAULT_PAGE_WAIT_MS)  # Give modal time to fully render

        # Take screenshot of modal
        try:
            page.screenshot(path="checkin_modal.png")
            logger.debug("Screenshot saved: checkin_modal.png")
        except Exception:
            pass

        # Select location if provided
        if location:
            try:
                logger.info(f"Attempting to select location: {location}")
                # Click location selector to open dropdown
                page.click(SELECTORS["location_selector"], timeout=SELECTOR_TIMEOUT_MS)
                page.wait_for_timeout(1000)

                # Try to find and click the location option
                # The dropdown options might have specific text
                if location.lower() == "telemunca":
                    # Try different possible text variations
                    location_options = [
                        'text="Telemunca"',
                        'text="Remote"',
                        'text="WFH"',
                        ':has-text("Telemunca")',
                    ]
                elif location.lower() == "birou":
                    location_options = [
                        'text="Birou"',
                        'text="Office"',
                        ':has-text("Birou")',
                    ]
                else:
                    location_options = [f'text="{location}"']

                location_selected = False
                for loc_selector in location_options:
                    try:
                        page.click(loc_selector, timeout=2000)
                        logger.info(f"Selected location using selector: {loc_selector}")
                        location_selected = True
                        break
                    except Exception:
                        continue

                if not location_selected:
                    logger.warning(f"Could not select location '{location}' - will proceed anyway")

                page.wait_for_timeout(1000)
            except Exception as e:
                logger.warning(f"Error selecting location: {e} - proceeding anyway")

        # The time fields should be pre-filled with current time
        # We don't need to modify them unless we want to
        logger.info("Time fields should be pre-filled")

        # Take screenshot before submitting
        try:
            page.screenshot(path="checkin_before_submit.png")
            logger.debug("Screenshot saved: checkin_before_submit.png")
        except Exception:
            pass

        # Click the submit button
        logger.info("Clicking submit button")
        page.click(SELECTORS["submit_button"], timeout=timeout)
        logger.info("Submit button clicked")

        # Wait for submission to complete
        page.wait_for_timeout(3000)
        page.wait_for_load_state("networkidle", timeout=timeout)

        # Take screenshot after submission
        try:
            page.screenshot(path="checkin_after.png")
            logger.debug("Screenshot saved: checkin_after.png")
        except Exception:
            pass

        # Look for success confirmation
        content = page.content().lower()
        if "success" in content or "pontaj inregistrat" in content or "inregistrat cu succes" in content or "successfully" in content:
            msg = f"Check-in successful at location={location}"
            logger.info(msg)
            return ("success", msg)
        elif "error" in content or "eroare" in content or "failed" in content:
            msg = f"Check-in failed - error message detected on page"
            logger.error(msg)
            return ("failure", msg)
        else:
            # Assume success if no error detected and modal closed
            # Check if modal is still visible
            try:
                if page.is_visible(SELECTORS["modal_body"], timeout=DEFAULT_PAGE_WAIT_MS):
                    msg = f"Check-in may have failed - modal still visible"
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
        # Save screenshot on timeout
        try:
            page.screenshot(path="checkin_timeout.png")
        except:
            pass
        return ("failure", msg)
    except Exception as e:
        msg = f"Error during check-in: {str(e)}"
        logger.error(msg)
        logger.debug(traceback.format_exc())
        # Save screenshot on error
        try:
            page.screenshot(path="checkin_error.png")
        except:
            pass
        return ("failure", msg)


def _perform_checkout(page: Page, location: Optional[str], timeout: int) -> Tuple[str, str]:
    """
    Perform check-out action on app.hriflow.ro

    Same flow as check-in - the system uses the same modal for both.
    Returns (status, message) tuple.
    """
    # Check-out uses the same modal and flow as check-in on this system
    logger.info("Check-out uses same flow as check-in on this system")
    return _perform_checkin(page, location, timeout)


def test_credentials(
    url: str,
    username: str,
    password: str,
    headless: bool = True,
    timeout: int = 30000
) -> Tuple[bool, str]:
    """
    Test if credentials are valid by attempting login.
    Returns (success, message) tuple.
    """
    logger.info(f"Testing credentials for user: {username}")

    try:
        with sync_playwright() as playwright:
            browser = _setup_browser(playwright, headless)
            context = browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()

            try:
                success = _login(page, url, username, password, timeout)

                if success:
                    return (True, "Login successful")
                else:
                    return (False, "Login failed - invalid credentials or website structure changed")

            finally:
                page.close()
                context.close()
                browser.close()

    except Exception as e:
        msg = f"Error testing credentials: {str(e)}"
        logger.error(msg)
        logger.debug(traceback.format_exc())
        return (False, msg)


def run_iso_check(
    event_type: str,
    location: Optional[str],
    user_settings: Optional[Dict[str, Any]] = None
) -> Tuple[str, str]:
    """
    Execute iFlow check-in or check-out using Playwright automation.

    Args:
        event_type: Either "checkIn" or "checkOut"
        location: Optional location ("telemunca" or "birou")
        user_settings: Optional dict with user's settings from Firestore
                      If None, falls back to environment variables

    Returns:
        Tuple of (status, message) where status is "success", "failure", or "skipped"
    """
    logger.info(f"=== Starting iFlow automation: {event_type} at location={location} ===")

    # Get configuration from user settings or environment
    if user_settings:
        logger.info("Using user-specific settings from Firestore")
        url = user_settings.get("iflowUrl", "https://app.hriflow.ro/#/dashboard")
        username = user_settings.get("iflowUsername", "")
        password = user_settings.get("iflowPassword", "")
        headless = user_settings.get("iflowHeadless", True)
        timeout = user_settings.get("iflowTimeout", 30000)
    else:
        logger.info("Using global settings from environment variables")
        url = os.getenv("IFLOW_URL", "https://app.hriflow.ro/#/dashboard")
        username = os.getenv("IFLOW_USERNAME", "")
        password = os.getenv("IFLOW_PASSWORD", "")
        headless = os.getenv("IFLOW_HEADLESS", "true").lower() == "true"
        timeout = int(os.getenv("IFLOW_TIMEOUT", "30000"))

    logger.info(f"Configuration: url={url}, username={username}, headless={headless}, timeout={timeout}ms")

    # Validate configuration
    if not username or not password:
        msg = "iFlow credentials not configured. Please configure credentials in Settings."
        logger.error(msg)
        return ("failure", msg)

    if not event_type:
        msg = "Event type not specified"
        logger.error(msg)
        return ("failure", msg)

    # Normalize event type
    event_type_lower = event_type.lower()
    if event_type_lower not in ["checkin", "checkout"]:
        msg = f"Unknown event type: {event_type}"
        logger.error(msg)
        return ("failure", msg)

    try:
        with sync_playwright() as playwright:
            browser = _setup_browser(playwright, headless)
            context = browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()

            try:
                # Perform login
                if not _login(page, url, username, password, timeout):
                    return ("failure", "Login failed - please check credentials")

                # Perform the appropriate action
                if event_type_lower == "checkin":
                    status, message = _perform_checkin(page, location, timeout)
                else:  # checkout
                    status, message = _perform_checkout(page, location, timeout)

                logger.info(f"=== iFlow automation completed: {status} - {message} ===")
                return (status, message)

            finally:
                # Clean up
                page.close()
                context.close()
                browser.close()
                logger.debug("Browser resources cleaned up")

    except Exception as e:
        msg = f"Unexpected error in iFlow automation: {str(e)}"
        logger.error(msg)
        logger.error(traceback.format_exc())
        return ("failure", msg)
