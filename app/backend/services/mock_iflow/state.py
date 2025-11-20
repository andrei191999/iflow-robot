"""
State management for mock iFlow server.

Allows configuring behavior (success, failures, delays) for testing.
"""

import logging
from typing import Literal, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


BehaviorMode = Literal["success", "login_fail", "timeout", "no_button", "submit_error"]


@dataclass
class MockState:
    """Configuration for mock iFlow server behavior."""

    # Behavior mode
    behavior: BehaviorMode = "success"

    # Simulated delays (milliseconds)
    page_load_delay: int = 500
    login_delay: int = 800
    modal_open_delay: int = 300
    submit_delay: int = 600

    # Session tracking
    logged_in_sessions: set = field(default_factory=set)

    # Credentials (for login validation)
    valid_credentials: dict = field(default_factory=lambda: {
        "demo@example.com": "demo123",
        "test@example.com": "test123"
    })

    # Statistics
    login_attempts: int = 0
    checkin_attempts: int = 0
    checkout_attempts: int = 0

    def reset_stats(self):
        """Reset statistics counters."""
        self.login_attempts = 0
        self.checkin_attempts = 0
        self.checkout_attempts = 0

    def is_valid_login(self, username: str, password: str) -> bool:
        """Check if credentials are valid."""
        return self.valid_credentials.get(username) == password

    def create_session(self) -> str:
        """Create a new session ID."""
        session_id = f"session_{datetime.utcnow().timestamp()}"
        self.logged_in_sessions.add(session_id)
        return session_id

    def is_logged_in(self, session_id: Optional[str]) -> bool:
        """Check if session is logged in."""
        return session_id in self.logged_in_sessions if session_id else False

    def should_succeed_login(self) -> bool:
        """Determine if login should succeed based on behavior mode."""
        return self.behavior != "login_fail"

    def should_show_checkin_button(self) -> bool:
        """Determine if check-in button should be visible."""
        return self.behavior != "no_button"

    def should_succeed_submit(self) -> bool:
        """Determine if form submission should succeed."""
        return self.behavior not in ["submit_error", "timeout"]

    def get_page_delay(self) -> int:
        """Get page load delay in ms."""
        if self.behavior == "timeout":
            return 60000  # 60 seconds to simulate timeout
        return self.page_load_delay

    def get_login_delay(self) -> int:
        """Get login processing delay in ms."""
        if self.behavior == "timeout":
            return 60000
        return self.login_delay

    def get_modal_delay(self) -> int:
        """Get modal opening delay in ms."""
        return self.modal_open_delay

    def get_submit_delay(self) -> int:
        """Get submit processing delay in ms."""
        if self.behavior == "timeout":
            return 60000
        return self.submit_delay


# Global state instance
_mock_state = MockState()


def get_mock_state() -> MockState:
    """Get the global mock state instance."""
    return _mock_state


def set_mock_behavior(
    behavior: BehaviorMode = "success",
    page_load_delay: Optional[int] = None,
    login_delay: Optional[int] = None,
    modal_open_delay: Optional[int] = None,
    submit_delay: Optional[int] = None
):
    """
    Configure mock server behavior.

    Args:
        behavior: Behavior mode (success, login_fail, timeout, no_button, submit_error)
        page_load_delay: Page load delay in ms
        login_delay: Login processing delay in ms
        modal_open_delay: Modal opening delay in ms
        submit_delay: Submit processing delay in ms
    """
    global _mock_state

    _mock_state.behavior = behavior

    if page_load_delay is not None:
        _mock_state.page_load_delay = page_load_delay
    if login_delay is not None:
        _mock_state.login_delay = login_delay
    if modal_open_delay is not None:
        _mock_state.modal_open_delay = modal_open_delay
    if submit_delay is not None:
        _mock_state.submit_delay = submit_delay

    logger.info(f"Mock behavior set to: {behavior}")


def reset_mock_state():
    """Reset mock state to defaults."""
    global _mock_state
    _mock_state = MockState()
    logger.info("Mock state reset to defaults")
