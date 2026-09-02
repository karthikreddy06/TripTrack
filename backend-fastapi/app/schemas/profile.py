from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    bio: Optional[str] = Field(default=None, max_length=500)
    travel_preferences: Optional[List[str]] = Field(default=None)
    home_currency: Optional[str] = Field(default=None, max_length=10)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip() if v is not None else None


class PasswordChange(BaseModel):
    current_password: str = Field(..., min_length=1, description="Current account password")
    new_password: str = Field(..., min_length=6, description="New password with at least 6 characters")
