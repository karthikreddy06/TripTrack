import ipaddress
import logging
import socket
import urllib.parse
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Response, status

from app.schemas.explore import (
    ExploreSearchResponse,
    DestinationSummary,
    PlaceDetailsResponse,
    PlaceItem,
    ExploreSuggestionItem
)
from app.services.explore.provider import explore_provider

logger = logging.getLogger("traveltrack.explore")

router = APIRouter(prefix="/explore", tags=["Explore & Travel Discovery (OpenStreetMap & Wikimedia)"])

ALLOWED_IMAGE_DOMAINS = [
    "wikimedia.org",
    "wikipedia.org",
    "openstreetmap.org",
    "w.wiki",
]

ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/avif",
    "image/gif",
}


def is_safe_image_proxy_url(target_url: str) -> bool:
    """
    Validate that target URL:
    1. Uses http or https protocol
    2. Has a hostname matching our allowed domain whitelist
    3. Resolves strictly to public, non-private, non-loopback IP addresses (SSRF protection)
    """
    try:
        parsed = urllib.parse.urlparse(target_url)
        if parsed.scheme not in ("http", "https"):
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        # Domain whitelist check (exact match or proper subdomain)
        is_domain_allowed = any(
            hostname == domain or hostname.endswith(f".{domain}")
            for domain in ALLOWED_IMAGE_DOMAINS
        )
        if not is_domain_allowed:
            logger.warning(f"Blocked image proxy request to unauthorized domain: {hostname}")
            return False

        # Resolve hostname to verify IP is not in private, loopback, or link-local ranges
        addr_info = socket.getaddrinfo(hostname, None)
        for entry in addr_info:
            ip_str = entry[4][0]
            ip = ipaddress.ip_address(ip_str)
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
            ):
                logger.warning(f"Blocked SSRF attempt resolving {hostname} to private/internal IP: {ip_str}")
                return False

        return True
    except Exception as exc:
        logger.warning(f"Error validating proxy URL '{target_url}': {exc}")
        return False


@router.get("/suggestions", response_model=List[ExploreSuggestionItem])
async def get_explore_suggestions(
    q: str = Query(..., min_length=1, max_length=100, description="Query string for autocomplete"),
    limit: int = Query(6, ge=1, le=10, description="Max suggestions to return")
):
    """
    Real-time autocomplete search suggestions with typo tolerance worldwide.
    """
    try:
        results = await explore_provider.get_suggestions(query=q, limit=limit)
        return [ExploreSuggestionItem(**item) for item in results]
    except Exception:
        return []


@router.get("/photo")
async def proxy_explore_photo(url: str = Query(..., description="Verified image URL to proxy")):
    """
    Proxy endpoint for Wikimedia / OpenStreetMap verified images to prevent 403 hotlink blocks.
    Protected against SSRF, internal network scanning, and DNS rebinding attacks.
    """
    if not url or not is_safe_image_proxy_url(url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or untrusted image URL"
        )

    headers = {
        "User-Agent": "TravelTrack-Discovery/3.0 (https://triptrack-frontend.onrender.com; info@triptrack.app)",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Referer": "https://en.wikipedia.org/"
    }

    try:
        # Avoid blind redirect following (SSRF redirect protection)
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=False) as client:
            current_url = url
            for _ in range(3):  # Allow at most 3 redirects, each strictly validated
                res = await client.get(current_url, headers=headers)
                if res.status_code in (301, 302, 303, 307, 308):
                    location = res.headers.get("Location")
                    if not location:
                        break
                    # Normalize relative redirect URLs
                    resolved_location = urllib.parse.urljoin(current_url, location)
                    if not is_safe_image_proxy_url(resolved_location):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Redirect to unauthorized location blocked"
                        )
                    current_url = resolved_location
                    continue

                if res.status_code == 200:
                    raw_content_type = res.headers.get("content-type", "image/jpeg").lower()
                    media_type = raw_content_type.split(";")[0].strip()

                    # Only serve verified image MIME types
                    if media_type not in ALLOWED_IMAGE_CONTENT_TYPES:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid image content type"
                        )

                    return Response(
                        content=res.content,
                        media_type=media_type,
                        headers={
                            "Cache-Control": "public, max-age=604800, immutable",
                            "Access-Control-Allow-Origin": "*",
                            "X-Content-Type-Options": "nosniff"
                        }
                    )
                break
    except HTTPException:
        raise
    except Exception as exc:
        logger.debug(f"Image proxy fetch error: {exc}")

    raise HTTPException(status_code=404, detail="Photo could not be retrieved")


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
    limit: int = Query(24, ge=1, le=100, description="Max results per page"),
    lat: Optional[float] = Query(None, description="Optional canonical latitude from selected suggestion"),
    lon: Optional[float] = Query(None, description="Optional canonical longitude from selected suggestion")
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
            limit=limit,
            lat=lat,
            lon=lon
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
