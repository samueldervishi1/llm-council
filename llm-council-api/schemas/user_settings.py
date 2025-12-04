from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

from constants.beta_features import get_available_beta_features


class UserSettings(BaseModel):
    """User preferences and settings."""
    user_id: str = Field(
        default="default",
        description="User identifier. Default 'default' for single-user mode."
    )

    # Data & Privacy
    auto_delete_days: Optional[int] = Field(
        default=None,
        description="Auto-delete sessions older than X days. None = never delete. Options: 30, 60, 90"
    )

    # Advanced - Beta Features
    enabled_beta_features: List[str] = Field(
        default=[],
        description="List of beta feature IDs that the user has opted into"
    )

    @field_validator('enabled_beta_features')
    @classmethod
    def validate_beta_features(cls, v: List[str]) -> List[str]:
        """Validate that all enabled features are valid beta features."""
        available = get_available_beta_features()
        invalid = [f for f in v if f not in available]
        if invalid:
            raise ValueError(f"Invalid beta features: {invalid}. Available: {available}")
        return v


class UserSettingsUpdate(BaseModel):
    """Request to update user settings. All fields are optional."""
    auto_delete_days: Optional[int] = Field(
        None,
        description="Auto-delete sessions older than X days. Options: 30, 60, 90, or null"
    )
    enabled_beta_features: Optional[List[str]] = Field(
        None,
        description="List of beta feature IDs to enable"
    )

    @field_validator('enabled_beta_features')
    @classmethod
    def validate_beta_features(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate that all enabled features are valid beta features."""
        if v is None:
            return v
        available = get_available_beta_features()
        invalid = [f for f in v if f not in available]
        if invalid:
            raise ValueError(f"Invalid beta features: {invalid}. Available: {available}")
        return v


class UserSettingsResponse(BaseModel):
    """Response containing user settings."""
    settings: UserSettings = Field(..., description="User settings object")
    message: str = Field(..., description="Status message")
