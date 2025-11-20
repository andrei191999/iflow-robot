"""
Schema models for demo/simulation endpoints.
"""

from typing import Literal, Optional, List, Dict
from pydantic import BaseModel, Field


class DemoRequest(BaseModel):
    """Request model for running a simulation."""

    mode: Literal["visual", "screenshot", "backend"] = Field(
        default="backend",
        description=(
            "Execution mode:\n"
            "- 'visual': Opens browser window (headless=false) for watching\n"
            "- 'screenshot': Headless but captures screenshots at each step\n"
            "- 'backend': Headless, no screenshots (production mode)"
        )
    )

    speed: Literal["slow", "normal", "fast"] = Field(
        default="normal",
        description=(
            "Execution speed:\n"
            "- 'slow': 2 second delays between steps\n"
            "- 'normal': 0.5 second delays between steps\n"
            "- 'fast': No artificial delays"
        )
    )

    scenario: Literal["check-in", "check-out"] = Field(
        default="check-in",
        description="Type of action to simulate"
    )

    location: Optional[Literal["telemunca", "birou"]] = Field(
        default=None,
        description="Work location to select (if applicable)"
    )

    use_mock: bool = Field(
        default=True,
        description="Use mock iFlow server instead of real one"
    )

    mock_behavior: Optional[Literal["success", "login_fail", "timeout", "no_button"]] = Field(
        default="success",
        description="Mock server behavior (only used if use_mock=true)"
    )


class SimulationStep(BaseModel):
    """Represents a single step in the simulation."""

    step_number: int = Field(description="Sequential step number (0-indexed)")
    name: str = Field(description="Human-readable step name")
    timestamp: str = Field(description="ISO timestamp when step started")
    duration_ms: int = Field(description="How long this step took in milliseconds")
    status: Literal["success", "warning", "error"] = Field(description="Step outcome")
    message: str = Field(description="Detailed message about what happened")
    screenshot_url: Optional[str] = Field(
        default=None,
        description="URL or path to screenshot (if captured)"
    )


class DemoResult(BaseModel):
    """Result of a simulation run."""

    success: bool = Field(description="Whether the simulation succeeded overall")
    duration_ms: int = Field(description="Total execution time in milliseconds")
    step_count: int = Field(description="Total number of steps executed")
    scenario: str = Field(description="What scenario was run")
    location: Optional[str] = Field(default=None, description="Location that was used")
    mode: str = Field(description="Execution mode that was used")

    steps: List[SimulationStep] = Field(
        default_factory=list,
        description="Detailed log of all steps"
    )

    screenshots: List[str] = Field(
        default_factory=list,
        description="List of all screenshot URLs/paths"
    )

    summary: str = Field(description="Human-readable summary of the run")
    error: Optional[str] = Field(
        default=None,
        description="Error message if the simulation failed"
    )


class PublicSimulationRequest(BaseModel):
    """Request for public simulation endpoint (no auth required)."""

    mode: Literal["visual"] = Field(
        default="visual",
        description="Execution mode: always visual for public demo"
    )

    speed: Literal["slow", "normal", "fast"] = Field(
        default="normal",
        description="Execution speed: slow, normal, or fast"
    )

    location: Optional[Literal["telemunca", "birou"]] = Field(
        default="telemunca",
        description="Work location to use for both check-in and check-out"
    )

    checkInTime: str = Field(
        default="09:00",
        description="Check-in time in HH:mm format"
    )

    checkOutTime: str = Field(
        default="17:00",
        description="Check-out time in HH:mm format"
    )


class PublicSimulationResult(BaseModel):
    """Combined result of check-in and check-out simulation."""

    success: bool = Field(description="Whether both simulations succeeded")
    total_duration_ms: int = Field(description="Total execution time for both operations")

    checkin_result: DemoResult = Field(description="Check-in simulation result")
    checkout_result: DemoResult = Field(description="Check-out simulation result")

    summary: str = Field(description="Human-readable summary of both runs")


class AdvancedSimulationRequest(BaseModel):
    """Request for advanced simulation with full schedule spec."""

    duration: Literal["1week", "1month", "3months"] = Field(
        description="Time period to simulate"
    )

    spec: Dict = Field(
        description="Full schedule specification (same format as regular schedules)"
    )

    mode: Literal["screenshot", "backend"] = Field(
        default="backend",
        description="Execution mode"
    )


class AdvancedSimulationEvent(BaseModel):
    """A single simulated event in advanced simulation."""

    date: str = Field(description="Date of event (YYYY-MM-DD)")
    time: str = Field(description="Time of event (HH:MM)")
    event_type: Literal["checkIn", "checkOut"] = Field(description="Type of event")
    location: Optional[str] = Field(description="Location for event")
    status: Literal["success", "failure", "skipped"] = Field(description="Event outcome")
    reason: Optional[str] = Field(default=None, description="Reason for skip/failure")


class AdvancedSimulationResult(BaseModel):
    """Result of advanced multi-period simulation."""

    success: bool = Field(description="Whether simulation completed successfully")
    total_events: int = Field(description="Total number of events simulated")
    successful_events: int = Field(description="Number of successful events")
    failed_events: int = Field(description="Number of failed events")
    skipped_events: int = Field(description="Number of skipped events (holidays, etc.)")
    success_rate: float = Field(description="Success rate as percentage (0-100)")

    events: List[AdvancedSimulationEvent] = Field(
        description="List of all simulated events"
    )

    sample_screenshots: List[str] = Field(
        default_factory=list,
        description="Sample screenshots from first few runs"
    )

    holiday_handling: Dict = Field(
        description="Statistics about holiday handling"
    )

    summary: str = Field(description="Human-readable summary")
    duration_ms: int = Field(description="Total simulation time")
