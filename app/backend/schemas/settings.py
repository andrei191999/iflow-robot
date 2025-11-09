from typing import Optional
from pydantic import BaseModel, Field


class IFlowCredentials(BaseModel):
    """User's iFlow credentials - stored encrypted in Firestore."""
    username: str = Field(..., description="iFlow username/email")
    password: str = Field(..., description="iFlow password")


class UserSettings(BaseModel):
    """User settings document."""
    uid: str
    iflowUrl: str = Field(default="https://app.hriflow.ro/#/dashboard", description="iFlow system URL")
    iflowUsername: Optional[str] = Field(default=None, description="iFlow username (stored encrypted)")
    iflowPassword: Optional[str] = Field(default=None, description="iFlow password (stored encrypted)")
    iflowHeadless: bool = Field(default=True, description="Run browser in headless mode")
    iflowTimeout: int = Field(default=30000, description="Operation timeout in milliseconds")


class UserSettingsUpdate(BaseModel):
    """Update user settings - all fields optional."""
    iflowUrl: Optional[str] = None
    iflowUsername: Optional[str] = None
    iflowPassword: Optional[str] = None
    iflowHeadless: Optional[bool] = None
    iflowTimeout: Optional[int] = None
