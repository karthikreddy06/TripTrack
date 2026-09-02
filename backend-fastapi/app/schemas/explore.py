from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class PlaceItem(BaseModel):
    place_id: str = Field(..., description="Canonical place identifier (Google Place ID or unique ID)")
    provider: str = Field("google", description="Data provider (google, verified, etc.)")
    provider_place_id: Optional[str] = Field(None, description="Raw provider place ID")
    name: str = Field(..., description="Verified name of the place, hotel, restaurant, or attraction")
    category: str = Field(..., description="Category: destination, hotel, restaurant, attraction, activity")
    location: str = Field(..., description="City, region, or administrative area")
    lat: Optional[float] = Field(None, description="Exact latitude coordinate")
    lon: Optional[float] = Field(None, description="Exact longitude coordinate")
    rating: Optional[float] = Field(None, description="Real user rating (0.0 - 5.0) if legitimately available")
    review_count: Optional[int] = Field(None, description="Real user review count if available")
    image_url: Optional[str] = Field(None, description="Verified primary photo URL directly belonging to this place (null if none)")
    photos: List[str] = Field(default_factory=list, description="List of verified photo URLs directly belonging to this place")
    description: Optional[str] = Field(None, description="Editorial summary or place description")
    address: Optional[str] = Field(None, description="Exact formatted street address")
    price_level: Optional[str] = Field(None, description="Price tier ($, $$, $$$, $$$$) if available")
    amenities: List[str] = Field(default_factory=list, description="Key amenities or features")
    cuisine: Optional[str] = Field(None, description="Cuisine type for dining")
    opening_hours: Optional[str] = Field(None, description="Operating hours if available")
    website: Optional[str] = Field(None, description="Official website URL")
    phone: Optional[str] = Field(None, description="International phone number")
    google_maps_uri: Optional[str] = Field(None, description="Direct Google Maps URL")
    tags: List[str] = Field(default_factory=list, description="Descriptive tags")

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
