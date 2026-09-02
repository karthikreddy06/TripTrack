from datetime import date
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ActivityCreate(BaseModel):
    trip_id: str = Field(..., min_length=1, description="Associated Trip ID")
    day_number: Optional[int] = Field(default=1, ge=1, le=100, description="Day number of the trip")
    date: str = Field(..., description="Activity date in YYYY-MM-DD format")
    time: Optional[str] = Field(default="", max_length=20, description="Activity time (e.g. 09:00 AM or 14:30)")
    title: str = Field(..., min_length=1, max_length=150, description="Activity title")
    location: Optional[str] = Field(default="", max_length=150, description="Location or venue")
    description: Optional[str] = Field(default="", max_length=1000, description="Activity details")
    cost: Optional[float] = Field(default=0.0, ge=0, description="Estimated or actual cost")
    notes: Optional[str] = Field(default="", max_length=1000, description="Extra tips/booking references")

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Activity title cannot be empty")
        return v.strip()

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("Date must be in valid YYYY-MM-DD format")
        return v


class ActivityUpdate(BaseModel):
    day_number: Optional[int] = Field(default=None, ge=1, le=100)
    date: Optional[str] = None
    time: Optional[str] = Field(default=None, max_length=20)
    title: Optional[str] = Field(default=None, min_length=1, max_length=150)
    location: Optional[str] = Field(default=None, max_length=150)
    description: Optional[str] = Field(default=None, max_length=1000)
    cost: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Activity title cannot be empty")
        return v.strip() if v is not None else None

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                date.fromisoformat(v)
            except ValueError:
                raise ValueError("Date must be in valid YYYY-MM-DD format")
        return v
