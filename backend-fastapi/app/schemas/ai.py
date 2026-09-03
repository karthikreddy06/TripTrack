from typing import List, Optional, Dict, Any
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


class PendingAction(BaseModel):
    action_id: str
    tool: str
    description: str
    args: Dict[str, Any] = Field(default_factory=dict)


class AIChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1500, description="User's natural language input")
    trip_id: Optional[str] = Field(default=None, description="Optional active trip ID context")
    conversation_id: Optional[str] = Field(default=None, description="Session conversation ID")
    confirm_action: Optional[bool] = Field(default=None, description="Confirmation flag for pending destructive action (true/false)")


class AIChatResponse(BaseModel):
    response: str
    conversation_id: str
    tool_called: Optional[str] = None
    tool_result: Optional[Any] = None
    pending_action: Optional[PendingAction] = None
    requires_confirmation: bool = False
    action_status: Optional[str] = None  # "executed", "pending_confirmation", "cancelled", "failed", "read_only"
    mutation_occurred: bool = False
    affected_entity: Optional[str] = None  # "trip", "itinerary", "expense", "wishlist"
    places: Optional[List[Dict[str, Any]]] = None


class ChatMessageItem(BaseModel):
    id: str
    role: str  # "user" | "assistant"
    content: str
    timestamp: str
    tool_called: Optional[str] = None
    tool_result: Optional[Any] = None
    action_status: Optional[str] = None
    pending_action: Optional[PendingAction] = None
    places: Optional[List[Dict[str, Any]]] = None


class ChatHistoryResponse(BaseModel):
    conversation_id: str
    messages: List[ChatMessageItem] = Field(default_factory=list)

