from datetime import date
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ActivityCreate(BaseModel):
    trip_id: str = Field(..., min_length=1, description="Associated Trip ID")
    day_number: Optional[int] = Field(default=1, ge=1, le=100, description="Day number of the trip")
    date: str = Field(..., description="Activity date in YYYY-MM-DD format")
    time: Optional[str] = Field(default="", max_length=50, description="Activity time (e.g. 09:00 AM or 14:30)")
    title: str = Field(..., min_length=1, max_length=200, description="Activity title")
    location: Optional[str] = Field(default="", max_length=300, description="Location, venue or address")
    description: Optional[str] = Field(default="", max_length=3000, description="Activity details")
    cost: Optional[float] = Field(default=0.0, ge=0, description="Estimated or actual cost")
    notes: Optional[str] = Field(default="", max_length=3000, description="Extra tips/booking references")
    place_id: Optional[str] = Field(default=None, description="Optional Google Place ID for discovered place")
    category: Optional[str] = Field(default=None, description="Category: attraction, hotel, restaurant, activity")
    image_url: Optional[str] = Field(default=None, description="Verified photo URL")

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
    time: Optional[str] = Field(default=None, max_length=50)
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    location: Optional[str] = Field(default=None, max_length=300)
    description: Optional[str] = Field(default=None, max_length=3000)
    cost: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=3000)
    place_id: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None

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
