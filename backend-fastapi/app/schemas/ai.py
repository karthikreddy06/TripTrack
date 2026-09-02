from typing import List, Optional, Dict
from pydantic import BaseModel, Field, field_validator


class AITripPlanRequest(BaseModel):
    destination: str = Field(..., min_length=1, max_length=150, description="Destination to plan for")
    days: int = Field(default=3, ge=1, le=30, description="Number of trip days")
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    travelers: int = Field(default=1, ge=1, le=50)
    budget: Optional[float] = Field(default=None, ge=0)
    interests: List[str] = Field(default_factory=list)
    travel_style: Optional[str] = Field(default="Balanced", max_length=50)
    anchor_place_id: Optional[str] = None
    anchor_place_name: Optional[str] = None
    selected_place_ids: List[str] = Field(default_factory=list)
    include_wishlist: bool = Field(default=True)

    @field_validator("destination")
    @classmethod
    def destination_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Destination cannot be empty")
        return v.strip()


class AITripActivity(BaseModel):
    time: str
    title: str
    location: str
    description: str
    place_id: Optional[str] = None
    category: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    distance_km: Optional[float] = None
    estimated_cost: float = 0.0


class AIDayPlan(BaseModel):
    day: int
    date: Optional[str] = ""
    theme: str
    rationale: Optional[str] = None  # Geographic and timing rationale for the cluster
    activities: List[AITripActivity]


class AITripPlanResponse(BaseModel):
    destination: str
    days: int
    summary: str
    itinerary_rationale: Optional[str] = None
    itinerary: List[AIDayPlan]
    packing_list: List[str]
    travel_tips: List[str]
    budget_breakdown: Dict[str, float]
    source: str = "ai"  # "ai" or "data_driven_cluster"


class AIBudgetAdviceRequest(BaseModel):
    trip_id: str = Field(..., min_length=1)


class AIBudgetAdviceResponse(BaseModel):
    trip_id: str
    status: str  # "on_track" | "caution" | "overbudget"
    summary: str
    analysis: str
    saving_tips: List[str]
    category_allocations: Dict[str, str]
