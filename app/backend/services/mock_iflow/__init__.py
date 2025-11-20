"""
Mock iFlow server for simulation and testing.

This package provides a fake iFlow HR platform implementation
that mimics the real app.hriflow.ro selectors and behavior.
"""

from .routes import router as mock_iflow_router
from .state import MockState, set_mock_behavior, get_mock_state

__all__ = [
    "mock_iflow_router",
    "MockState",
    "set_mock_behavior",
    "get_mock_state"
]
