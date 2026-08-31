from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator


class TripCreate(BaseModel):
    user_id: str = Field(..., min_length=1, description="Owner user ID")
    destination: str = Field(..., min_length=1, description="Trip destination")
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")
    status: Literal["planned", "ongoing", "completed", "cancelled"] = "planned"
    budget: float = Field(..., ge=0, description="Trip budget (must be non-negative)")

    @field_validator("destination")
    @classmethod
    def destination_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Destination cannot be empty or whitespace")
        return v.strip()

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("Date must be in valid YYYY-MM-DD format")
        return v

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date and self.end_date:
            d_start = date.fromisoformat(self.start_date)
            d_end = date.fromisoformat(self.end_date)
            if d_end < d_start:
                raise ValueError("end_date must not be before start_date")
        return self


class TripUpdate(BaseModel):
    destination: str | None = Field(default=None, min_length=1)
    start_date: str | None = None
    end_date: str | None = None
    status: Literal["planned", "ongoing", "completed", "cancelled"] | None = None
    budget: float | None = Field(default=None, ge=0)

    @field_validator("destination")
    @classmethod
    def destination_must_not_be_blank(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("Destination cannot be empty or whitespace")
        return v.strip() if v is not None else None

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date_format(cls, v: str | None) -> str | None:
        if v is not None:
            try:
                date.fromisoformat(v)
            except ValueError:
                raise ValueError("Date must be in valid YYYY-MM-DD format")
        return v

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date is not None and self.end_date is not None:
            d_start = date.fromisoformat(self.start_date)
            d_end = date.fromisoformat(self.end_date)
            if d_end < d_start:
                raise ValueError("end_date must not be before start_date")
        return self