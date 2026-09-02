from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class WishlistItemCreate(BaseModel):
    place_id: str = Field(..., description="Unique place identifier from Explore provider")
    name: str = Field(..., min_length=1, max_length=200, description="Name of the place, hotel, restaurant, or attraction")
    category: str = Field("destination", description="Category: destination, hotel, restaurant, attraction, activity")
    location: str = Field(..., min_length=1, max_length=200, description="City, country, or address")
    image_url: Optional[str] = Field(None, description="Image URL if legitimately available")
    rating: Optional[float] = Field(None, ge=0, le=5, description="Legitimate rating if available")
    description: Optional[str] = Field(None, description="Brief description")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata such as coordinates, price level, amenities, website")

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
