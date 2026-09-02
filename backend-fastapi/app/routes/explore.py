from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.explore import (
    ExploreSearchResponse,
    DestinationSummary,
    PlaceDetailsResponse,
    PlaceItem
)
from app.services.explore.provider import explore_provider

router = APIRouter(prefix="/explore", tags=["Explore & Travel Discovery (OpenStreetMap & Wikimedia)"])


@router.get("/featured", response_model=List[DestinationSummary])
async def get_featured_destinations():
    """
    Retrieve curated featured destinations for the Explore landing page.
    """
    try:
        featured = await explore_provider.get_featured_destinations()
        return [DestinationSummary(**d) for d in featured]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to load featured destinations: {str(e)}"
        )


@router.get("/search", response_model=ExploreSearchResponse)
async def search_explore(
    q: str = Query(..., min_length=1, max_length=100, description="Destination or place search query"),
    category: str = Query("all", description="Filter category: all, attractions, hotels, restaurants, cafes, museums, parks, historic, activities"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    limit: int = Query(24, ge=1, le=100, description="Max results per page")
):
    """
    Search for places, attractions, dining, cafes, and stays via Nominatim, Overpass API, and Wikimedia.
    No API keys, no Google, no Mapbox.
    """
    try:
        results = await explore_provider.search_places(
            query=q,
            category=category,
            page=page,
            limit=limit
        )
        return ExploreSearchResponse(**results)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to process search at this time: {str(e)}"
        )


@router.get("/destinations/{destination}", response_model=DestinationSummary)
async def get_destination(destination: str):
    """
    Retrieve full destination overview, highlights, hotels, restaurants, and attractions.
    """
    dest_data = await explore_provider.get_destination_details(destination)
    if not dest_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Destination '{destination}' could not be located."
        )
    return DestinationSummary(**dest_data)


@router.get("/places/{place_id}", response_model=PlaceDetailsResponse)
async def get_place(place_id: str):
    """
    Retrieve full details for a place with coordinates, verified photo, and source attribution.
    """
    place_data = await explore_provider.get_place_by_id(place_id)
    if not place_data or not place_data.get("place"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Place with ID '{place_id}' not found."
        )

    return PlaceDetailsResponse(
        place=PlaceItem(**place_data["place"]),
        nearby_places=[PlaceItem(**p) for p in place_data.get("nearby_places", [])]
    )


@router.get("/hotels", response_model=List[PlaceItem])
async def get_explore_hotels(
    destination: str = Query("Hyderabad", description="City to discover hotels in"),
    limit: int = Query(12, ge=1, le=50)
):
    """
    Direct endpoint for hotels in a destination.
    """
    res = await explore_provider.search_places(query=destination, category="hotels", limit=limit)
    return [PlaceItem(**p) for p in res.get("places", [])]


@router.get("/restaurants", response_model=List[PlaceItem])
async def get_explore_restaurants(
    destination: str = Query("Hyderabad", description="City to discover restaurants and cafes in"),
    limit: int = Query(12, ge=1, le=50)
):
    """
    Direct endpoint for restaurants and dining in a destination.
    """
    res = await explore_provider.search_places(query=destination, category="restaurants", limit=limit)
    return [PlaceItem(**p) for p in res.get("places", [])]


@router.get("/attractions", response_model=List[PlaceItem])
async def get_explore_attractions(
    destination: str = Query("Hyderabad", description="City to discover sights and attractions in"),
    limit: int = Query(12, ge=1, le=50)
):
    """
    Direct endpoint for attractions and landmarks in a destination.
    """
    res = await explore_provider.search_places(query=destination, category="attractions", limit=limit)
    return [PlaceItem(**p) for p in res.get("places", [])]
