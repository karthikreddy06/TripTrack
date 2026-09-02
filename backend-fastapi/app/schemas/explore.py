from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class PlaceItem(BaseModel):
    place_id: str = Field(..., description="Unique identifier for place")
    name: str = Field(..., description="Name of the place, hotel, restaurant, or attraction")
    category: str = Field(..., description="Category: destination, hotel, restaurant, attraction, activity")
    location: str = Field(..., description="City, region, or address")
    lat: Optional[float] = Field(None, description="Latitude coordinate")
    lon: Optional[float] = Field(None, description="Longitude coordinate")
    rating: Optional[float] = Field(None, description="Legitimate rating if available")
    image_url: Optional[str] = Field(None, description="Representative image URL")
    description: Optional[str] = Field(None, description="Description or overview")
    address: Optional[str] = Field(None, description="Full street address if available")
    price_level: Optional[str] = Field(None, description="Price tier ($, $$, $$$, $$$$) if available")
    amenities: Optional[List[str]] = Field(default_factory=list, description="Key amenities or features")
    cuisine: Optional[str] = Field(None, description="Cuisine type for dining")
    opening_hours: Optional[str] = Field(None, description="Operating hours if available")
    website: Optional[str] = Field(None, description="Official website or contact URL")
    tags: Optional[List[str]] = Field(default_factory=list, description="Descriptive tags")

class DestinationSummary(BaseModel):
    destination: str
    country: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    overview: Optional[str] = None
    best_time_to_visit: Optional[str] = None
    currency: Optional[str] = None
    highlights: List[PlaceItem] = Field(default_factory=list)
    hotels: List[PlaceItem] = Field(default_factory=list)
    restaurants: List[PlaceItem] = Field(default_factory=list)
    attractions: List[PlaceItem] = Field(default_factory=list)
    activities: List[PlaceItem] = Field(default_factory=list)

class ExploreSearchResponse(BaseModel):
    query: str
    category: str = "all"
    total_results: int
    results: List[PlaceItem] = Field(default_factory=list)
    destination_info: Optional[DestinationSummary] = None

class PlaceDetailsResponse(BaseModel):
    place: PlaceItem
    nearby_places: List[PlaceItem] = Field(default_factory=list)
