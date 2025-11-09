from typing import Optional, Literal, List
from pydantic import BaseModel, Field

LocationValue = Literal["telemunca", "birou"]  # simple dropdown

class HourWindow(BaseModel):
    # Day-of-week short name (Mon..Sun) OR a specific date "YYYY-MM-DD"
    day: str
    start: str  # "HH:MM"
    end: str    # "HH:MM"
    action: Literal["exclude", "include"] = "exclude"

class DayConfig(BaseModel):
    enabled: bool = False
    checkIn: Optional[str] = None   # "HH:MM"
    checkOut: Optional[str] = None  # "HH:MM"
    location: Optional[LocationValue] = None

class WeekConfig(BaseModel):
    Mon: DayConfig = DayConfig()
    Tue: DayConfig = DayConfig()
    Wed: DayConfig = DayConfig()
    Thu: DayConfig = DayConfig()
    Fri: DayConfig = DayConfig()
    Sat: DayConfig = DayConfig()
    Sun: DayConfig = DayConfig()

class Jitter(BaseModel):
    minutesMinus: int = 0
    minutesPlus: int = 0

class Holidays(BaseModel):
    publicCalendars: List[str] = Field(default_factory=list)  # e.g., ["RO"]
    personalDates: List[str] = Field(default_factory=list)    # ISO dates
    behavior: Literal["skip", "move_to_next_workday", "run_anyway"] = "skip"

class ExceptionsCfg(BaseModel):
    include: List[str] = Field(default_factory=list)  # ISO "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM"
    exclude: List[str] = Field(default_factory=list)  # same formats; exclude wins over include
    hourWindows: List[HourWindow] = Field(default_factory=list)  # per-day or per-date time windows

class ScheduleSpec(BaseModel):
    tz: str = "Europe/Bucharest"
    week: WeekConfig = WeekConfig()
    jitter: Jitter = Jitter()
    holidays: Holidays = Holidays()
    exceptions: ExceptionsCfg = ExceptionsCfg()

class NextEvent(BaseModel):
    type: Literal["checkIn", "checkOut"]
    at: str        # UTC ISO timestamp
    localDate: str # YYYY-MM-DD
    location: Optional[str] = None

class ScheduleDoc(BaseModel):
    uid: str
    name: str
    active: bool = True
    spec: ScheduleSpec
    next_event: Optional[NextEvent] = None

class RunDoc(BaseModel):
    scheduleId: str
    uid: str
    eventType: Literal["checkIn", "checkOut"]
    scheduledAt: str
    status: Literal["success", "failure", "skipped"] = "success"
    message: Optional[str] = None
    location: Optional[LocationValue] = None
