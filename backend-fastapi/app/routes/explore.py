from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Response, status
from fastapi.responses import Response

from app.schemas.explore import (
    ExploreSearchResponse,
    DestinationSummary,
    PlaceDetailsResponse,
    PlaceItem
)
from app.services.places_provider import places_provider, VERIFIED_DESTINATIONS
from app.services.google_places_provider import google_places_provider, VERIFIED_REAL_PLACES

router = APIRouter(prefix="/explore", tags=["Explore & Travel Discovery"])


@router.get("/featured", response_model=List[DestinationSummary])
async def get_featured_destinations():
    """
    Retrieve curated featured destinations for the Explore landing page.
    """
    featured = []
    for key, data in VERIFIED_DESTINATIONS.items():
        places = [VERIFIED_REAL_PLACES[pid] for pid in data.get("place_ids", []) if pid in VERIFIED_REAL_PLACES]
        featured.append(
            DestinationSummary(
                destination=data["destination"],
                country=data["country"],
                lat=data["lat"],
                lon=data["lon"],
                description=data["description"],
                image_url=data["image_url"],
                overview=data["overview"],
                best_time_to_visit=data["best_time_to_visit"],
                currency=data["currency"],
                highlights=[PlaceItem(**p) for p in places if p["category"] in ["attraction", "activity"]],
                hotels=[PlaceItem(**p) for p in places if p["category"] == "hotel"],
                restaurants=[PlaceItem(**p) for p in places if p["category"] == "restaurant"],
                attractions=[PlaceItem(**p) for p in places if p["category"] == "attraction"],
                activities=[PlaceItem(**p) for p in places if p["category"] == "activity"],
            )
        )
    return featured


@router.get("/search", response_model=ExploreSearchResponse)
async def search_explore(
    q: str = Query(..., min_length=1, max_length=100, description="Destination or place search query"),
    category: str = Query("all", description="Filter category: all, destinations, hotels, restaurants, attractions, activities"),
    limit: int = Query(30, ge=1, le=100, description="Max results to return")
):
    """
    Search for destinations, hotels, restaurants, attractions, and activities.
    """
    try:
        results = await places_provider.search_places(query=q, category=category, limit=limit)
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
    dest_data = await places_provider.get_destination_details(destination)
    if not dest_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Destination '{destination}' not found."
        )
    return DestinationSummary(**dest_data)


@router.get("/places/photo")
async def get_place_photo(
    photo_ref: str = Query(..., min_length=1, description="Google Places photo reference name"),
    max_width: int = Query(1200, ge=100, le=2400)
):
    """
    Proxy Google Places photo securely using backend credentials.
    Returns cached image bytes with caching headers to eliminate client-side key exposure.
    """
    photo_bytes = await google_places_provider.get_photo_media(photo_ref=photo_ref, max_width=max_width)
    if not photo_bytes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found or Google Places API key not configured."
        )

    return Response(
        content=photo_bytes,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "public, max-age=86400, immutable"
        }
    )


@router.get("/places/{place_id}", response_model=PlaceDetailsResponse)
async def get_place_details(place_id: str):
    """
    Retrieve detailed information and nearby spots for a specific place using canonical Google Place ID.
    """
    place_info = await places_provider.get_place_by_id(place_id)
    if not place_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Place with ID '{place_id}' not found."
        )
    return PlaceDetailsResponse(**place_info)


@router.get("/hotels", response_model=ExploreSearchResponse)
async def get_hotels(
    q: str = Query(..., min_length=1, description="Location to search hotels in"),
    limit: int = Query(30, ge=1, le=100)
):
    """
    Dedicated endpoint for hotel and accommodations discovery.
    """
    results = await places_provider.search_places(query=q, category="hotels", limit=limit)
    return ExploreSearchResponse(**results)


@router.get("/restaurants", response_model=ExploreSearchResponse)
async def get_restaurants(
    q: str = Query(..., min_length=1, description="Location to search dining in"),
    limit: int = Query(30, ge=1, le=100)
):
    """
    Dedicated endpoint for restaurant and culinary discovery.
    """
    results = await places_provider.search_places(query=q, category="restaurants", limit=limit)
    return ExploreSearchResponse(**results)


@router.get("/attractions", response_model=ExploreSearchResponse)
async def get_attractions(
    q: str = Query(..., min_length=1, description="Location to search sights in"),
    limit: int = Query(30, ge=1, le=100)
):
    """
    Dedicated endpoint for attractions and activities discovery.
    """
    results = await places_provider.search_places(query=q, category="attractions", limit=limit)
    return ExploreSearchResponse(**results)
