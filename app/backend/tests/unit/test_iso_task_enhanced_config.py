
import os
import pytest
from unittest.mock import patch, MagicMock
from services.iso_task_enhanced import run_iso_check_enhanced

@patch("services.iso_task_enhanced.SimulationLogger")
@patch("services.iso_task_enhanced.sync_playwright")
@patch("services.iso_task_enhanced._setup_browser")
def test_cloud_run_headless_override(mock_setup_browser, mock_playwright, mock_logger):
    """Verify that K_SERVICE env var forces headless=True"""

    # Mock logger
    mock_logger.return_value.get_total_duration_ms.return_value = 100
    mock_logger.return_value.steps = []

    # Mock playwright
    mock_pw_instance = MagicMock()
    mock_playwright.return_value.start.return_value = mock_pw_instance
    mock_browser = MagicMock()
    mock_setup_browser.return_value = mock_browser
    mock_context = mock_browser.new_context.return_value
    mock_page = mock_context.new_page.return_value
    mock_page.goto.return_value = None

    # Helper to run the check
    def run_check():
        return run_iso_check_enhanced(
            event_type="checkIn",
            location="birou",
            close_browser_on_exit=True,
            user_settings={"iflowUsername": "u", "iflowPassword": "p"}
        )

    # Case 1: NO K_SERVICE. headless should follow input/default
    with patch.dict(os.environ, {"IFLOW_USERNAME": "u", "IFLOW_PASSWORD": "p"}, clear=True):
         # If no K_SERVICE, logic is default.
         # In code: headless = user_settings.get("iflowHeadless", True)
         # We passed user_settings without "iflowHeadless", so defaults True.
         run_check()
         # Check call arguments
         args, _ = mock_setup_browser.call_args
         # _setup_browser(playwright, headless)
         assert args[1] is True, "Default headless should be True"

    mock_setup_browser.reset_mock()

    # Case 2: K_SERVICE present. Force True even if settings say False
    with patch.dict(os.environ, {"K_SERVICE": "my-service", "IFLOW_USERNAME": "u", "IFLOW_PASSWORD": "p"}, clear=True):
         # Pass explicit False in settings
         run_iso_check_enhanced(
            event_type="checkIn",
            location="birou",
            close_browser_on_exit=True,
            user_settings={"iflowUsername": "u", "iflowPassword": "p", "iflowHeadless": False}
        )
         args, _ = mock_setup_browser.call_args
         assert args[1] is True, "Should force headless=True when K_SERVICE is present"

    mock_setup_browser.reset_mock()
