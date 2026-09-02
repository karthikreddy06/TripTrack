from datetime import date
from typing import Literal, Optional, Dict
from pydantic import BaseModel, Field, field_validator

ExpenseCategory = Literal[
    "Accommodation",
    "Food",
    "Transport",
    "Activities",
    "Shopping",
    "Other"
]

class ExpenseCreate(BaseModel):
    trip_id: str = Field(..., min_length=1, description="Associated Trip ID")
    category: ExpenseCategory = Field(..., description="Expense category")
    amount: float = Field(..., gt=0, description="Expense amount (must be positive)")
    date: str = Field(..., description="Expense date in YYYY-MM-DD format")
    description: str = Field(..., min_length=1, max_length=250, description="Description of the expense")

    @field_validator("description")
    @classmethod
    def description_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Description cannot be empty")
        return v.strip()

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("Date must be in valid YYYY-MM-DD format")
        return v


class ExpenseUpdate(BaseModel):
    category: Optional[ExpenseCategory] = None
    amount: Optional[float] = Field(default=None, gt=0)
    date: Optional[str] = None
    description: Optional[str] = Field(default=None, min_length=1, max_length=250)

    @field_validator("description")
    @classmethod
    def description_must_not_be_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Description cannot be empty")
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


class BudgetSummary(BaseModel):
    trip_id: str
    budget: float
    total_spent: float
    remaining_budget: float
    percentage_spent: float
    expense_count: int
    by_category: Dict[str, float]
