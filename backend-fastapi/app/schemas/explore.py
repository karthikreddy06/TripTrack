from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field


class PlaceSource(BaseModel):
    provider: str = "openstreetmap"
    source_url: Optional[str] = None


class PlaceLocation(BaseModel):
    lat: float
    lon: float


class PlaceItem(BaseModel):
    id: Optional[str] = Field(None, description="Unique place identifier")
    place_id: Optional[str] = Field(None, description="Place identifier for backward compatibility")
    provider: str = Field("openstreetmap", description="Data provider (openstreetmap, wikimedia, etc.)")
    provider_id: Optional[str] = Field(None, description="Provider entity ID (e.g. node/12345)")
    name: str = Field(..., description="Name of the place, attraction, hotel, cafe, or restaurant")
    category: str = Field(..., description="Category: attraction, museum, historic, park, hotel, restaurant, cafe, activity")
    address: Optional[str] = Field(None, description="Formatted street address")
    location: Optional[Union[PlaceLocation, str, Dict[str, Any]]] = Field(None, description="Location coordinates or city name")
    lat: Optional[float] = Field(None, description="Latitude coordinate")
    lon: Optional[float] = Field(None, description="Longitude coordinate")
    description: Optional[str] = Field(None, description="Verified summary or editorial description")
    rating: Optional[float] = Field(None, description="Rating if legitimately available (null if none)")
    review_count: Optional[int] = Field(None, description="Review count if legitimately available (null if none)")
    image_url: Optional[str] = Field(None, description="Verified image URL (null if not verified)")
    photos: List[str] = Field(default_factory=list, description="List of verified image URLs")
    image_verified: bool = Field(False, description="True ONLY when photo is confirmed for this exact entity")
    image_source: Optional[str] = Field(None, description="Source of the verified photo (wikipedia, wikimedia_commons)")
    image_source_url: Optional[str] = Field(None, description="Original source page URL for attribution")
    image_author: Optional[str] = Field(None, description="Author / photographer attribution")
    image_license: Optional[str] = Field(None, description="Creative Commons license type")
    wikipedia_url: Optional[str] = Field(None, description="Wikipedia article URL")
    wikidata_id: Optional[str] = Field(None, description="Wikidata entity ID")
    phone: Optional[str] = Field(None, description="Contact phone")
    website: Optional[str] = Field(None, description="Official website")
    opening_hours: Optional[str] = Field(None, description="Opening hours")
    tags: List[str] = Field(default_factory=list, description="Descriptive tags")
    source: Optional[Union[PlaceSource, Dict[str, Any]]] = Field(None, description="Source provenance")


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
    places: List[PlaceItem] = Field(default_factory=list)
    page: int = 1
    limit: int = 24
    has_more: bool = False
    destination_info: Optional[DestinationSummary] = None


class PlaceDetailsResponse(BaseModel):
    place: PlaceItem
    nearby_places: List[PlaceItem] = Field(default_factory=list)
