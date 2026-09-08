from datetime import datetime, timezone
from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator

class WishlistItemCreate(BaseModel):
    place_id: str = Field(..., description="Unique place identifier from Explore provider")
    name: str = Field(..., min_length=1, max_length=300, description="Name of the place, hotel, restaurant, or attraction")
    category: str = Field("destination", description="Category: destination, hotel, restaurant, attraction, activity")
    location: Any = Field(default="Destination", description="City, country, address, or coordinate dictionary")
    image_url: Optional[str] = Field(None, description="Image URL if legitimately available")
    rating: Optional[float] = Field(None, ge=0, le=5, description="Legitimate rating if available")
    description: Optional[str] = Field(None, description="Brief description")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata such as coordinates, price level, amenities, website")

    @field_validator("location", mode="before")
    @classmethod
    def normalize_location(cls, v: Any) -> str:
        if isinstance(v, str):
            clean = v.strip()[:300]
            return clean if clean else "Destination"
        if isinstance(v, dict):
            if "address" in v and isinstance(v["address"], str) and v["address"].strip():
                return v["address"].strip()[:300]
            if "city" in v and isinstance(v["city"], str) and v["city"].strip():
                return v["city"].strip()[:300]
            lat = v.get("lat") or v.get("latitude")
            lon = v.get("lon") or v.get("longitude") or v.get("lng")
            if lat is not None and lon is not None:
                return f"{lat}, {lon}"
            return "Destination"
        return "Destination"

class WishlistItemResponse(BaseModel):
    id: str = Field(..., alias="_id")
    user_id: str
    place_id: str
    name: str
    category: str
    location: str
    image_url: Optional[str] = None
    rating: Optional[float] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None

    model_config = {
        "populate_by_name": True,
        "json_encoders": {
            datetime: lambda dt: dt.isoformat()
        }
    }

class WishlistCheckResponse(BaseModel):
    is_saved: bool
    wishlist_id: Optional[str] = None

