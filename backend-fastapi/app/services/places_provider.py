import time
import urllib.parse
from typing import Dict, List, Optional, Any
from app.services.google_places_provider import google_places_provider, VERIFIED_REAL_PLACES
from app.services.image_provider import image_provider

# In-memory cache with TTL (2 hours)
_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 7200

# Curated top destinations with verified geographic coordinates and currency
POPULAR_DESTINATIONS_META = {
    "hyderabad": {"destination": "Hyderabad", "country": "India", "lat": 17.3850, "lon": 78.4867, "currency": "INR (₹)", "best_time": "October to March"},
    "goa": {"destination": "Goa", "country": "India", "lat": 15.2993, "lon": 74.1240, "currency": "INR (₹)", "best_time": "November to February"},
    "bengaluru": {"destination": "Bengaluru", "country": "India", "lat": 12.9716, "lon": 77.5946, "currency": "INR (₹)", "best_time": "September to March"},
    "delhi": {"destination": "Delhi", "country": "India", "lat": 28.6139, "lon": 77.2090, "currency": "INR (₹)", "best_time": "October to March"},
    "mumbai": {"destination": "Mumbai", "country": "India", "lat": 18.9220, "lon": 72.8347, "currency": "INR (₹)", "best_time": "November to February"},
    "paris": {"destination": "Paris", "country": "France", "lat": 48.8566, "lon": 2.3522, "currency": "EUR (€)", "best_time": "April to October"},
    "london": {"destination": "London", "country": "United Kingdom", "lat": 51.5074, "lon": -0.1278, "currency": "GBP (£)", "best_time": "May to September"},
    "dubai": {"destination": "Dubai", "country": "UAE", "lat": 25.2048, "lon": 55.2708, "currency": "AED (د.إ)", "best_time": "November to March"},
    "tokyo": {"destination": "Tokyo", "country": "Japan", "lat": 35.6762, "lon": 139.6503, "currency": "JPY (¥)", "best_time": "March to May, Sept to Nov"},
    "singapore": {"destination": "Singapore", "country": "Singapore", "lat": 1.3521, "lon": 103.8198, "currency": "SGD (S$)", "best_time": "Year-round"},
    "tirupati": {"destination": "Tirupati", "country": "India", "lat": 13.6288, "lon": 79.4192, "currency": "INR (₹)", "best_time": "September to February"},
    "jaipur": {"destination": "Jaipur", "country": "India", "lat": 26.9124, "lon": 75.7873, "currency": "INR (₹)", "best_time": "October to March"}
}


class PlacesProvider:
    """
    High-level Places Provider delegating to GooglePlacesProvider with
    Wikipedia and Foursquare verified photo resolution.
    """

    def __init__(self):
        self.google_provider = google_places_provider
        self.image_provider = image_provider

    def _get_cache(self, key: str) -> Optional[Any]:
        cached = _CACHE.get(key)
        if cached and (time.time() - cached["timestamp"]) < CACHE_TTL_SECONDS:
            return cached["data"]
        return None

    def _set_cache(self, key: str, data: Any):
        _CACHE[key] = {
            "timestamp": time.time(),
            "data": data
        }

    async def _enrich_place_photos(self, place: Dict[str, Any]) -> Dict[str, Any]:
        """
        If a place lacks verified photos from Google Places, attempt verified Wikipedia resolution.
        """
        if not place.get("image_url") and not place.get("photos"):
            img_info = await self.image_provider.resolve_place_image(
                place_name=place.get("name", ""),
                category=place.get("category", "attraction"),
                location=place.get("location", ""),
                lat=place.get("lat"),
                lon=place.get("lon"),
            )
            if img_info and img_info.get("image_url"):
                place["image_url"] = img_info["image_url"]
                place["photos"] = [img_info["image_url"]]
                if not place.get("description") and img_info.get("description"):
                    place["description"] = img_info["description"]
                if img_info.get("source_page"):
                    place["source_url"] = img_info["source_page"]
        return place

    async def search_places(
        self,
        query: str,
        category: str = "all",
        limit: int = 30
    ) -> Dict[str, Any]:
        """
        Search for places globally using Google Places + ImageProvider enrichment.
        """
        res = await self.google_provider.search_places(query=query, category=category, limit=limit)
        results = res.get("results", [])

        # Enrich results with verified images if missing
        enriched_results = []
        for p in results:
            enriched = await self._enrich_place_photos(dict(p))
            enriched_results.append(enriched)

        res["results"] = enriched_results

        # Resolve destination metadata if query matches a destination
        dest_summary = await self.get_destination_details(query)
        res["destination_info"] = dest_summary

        return res

    async def get_destination_details(self, destination_name: str) -> Optional[Dict[str, Any]]:
        """
        Get structured destination guide with verified places, coordinates, and Wikipedia overview.
        """
        norm = destination_name.lower().strip()
        cache_key = f"dest_details:{norm}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        # Check known destination metadata
        meta = None
        for k, v in POPULAR_DESTINATIONS_META.items():
            if k in norm or norm in k:
                meta = v
                break

        # Query Wikipedia for destination overview & hero image
        wiki_info = await self.image_provider.resolve_wikipedia_image(destination_name)
        image_url = wiki_info.get("image_url") if wiki_info else None
        description = wiki_info.get("description") if wiki_info else None

        # Fetch places in destination
        search_res = await self.google_provider.search_places(destination_name, category="all", limit=20)
        places = search_res.get("results", [])

        enriched_places = []
        for p in places:
            enriched = await self._enrich_place_photos(dict(p))
            enriched_places.append(enriched)

        if not meta and not places and not wiki_info:
            self._set_cache(cache_key, None)
            return None

        dest_title = meta["destination"] if meta else destination_name.title()
        lat = meta["lat"] if meta else (enriched_places[0]["lat"] if enriched_places and enriched_places[0].get("lat") else None)
        lon = meta["lon"] if meta else (enriched_places[0]["lon"] if enriched_places and enriched_places[0].get("lon") else None)

        guide = {
            "destination": dest_title,
            "country": meta.get("country", "") if meta else "",
            "lat": lat,
            "lon": lon,
            "description": description or f"Discover the culture, landmarks, and sights of {dest_title}.",
            "image_url": image_url or (enriched_places[0].get("image_url") if enriched_places else None),
            "overview": description or f"{dest_title} offers a curated blend of historic monuments, culinary experiences, and attractions.",
            "best_time_to_visit": meta.get("best_time", "Year-round") if meta else "October to April",
            "currency": meta.get("currency", "USD ($)") if meta else "USD ($)",
            "highlights": [p for p in enriched_places if p.get("category") in ["attraction", "activity"]],
            "hotels": [p for p in enriched_places if p.get("category") == "hotel"],
            "restaurants": [p for p in enriched_places if p.get("category") == "restaurant"],
            "attractions": [p for p in enriched_places if p.get("category") == "attraction"],
            "activities": [p for p in enriched_places if p.get("category") == "activity"],
        }

        self._set_cache(cache_key, guide)
        return guide

    async def get_featured_destinations(self) -> List[Dict[str, Any]]:
        """
        Retrieve list of featured destination guides.
        """
        cache_key = "featured_destinations"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        featured = []
        for name in ["hyderabad", "goa", "bengaluru", "delhi", "mumbai", "paris"]:
            guide = await self.get_destination_details(name)
            if guide:
                featured.append(guide)

        self._set_cache(cache_key, featured)
        return featured

    async def get_place_by_id(self, place_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve place details by canonical Google Place ID + Image Provider enrichment.
        """
        res = await self.google_provider.get_place_by_id(place_id)
        if res and res.get("place"):
            res["place"] = await self._enrich_place_photos(dict(res["place"]))
            if res.get("nearby_places"):
                res["nearby_places"] = [await self._enrich_place_photos(dict(p)) for p in res["nearby_places"]]
        return res


# Singleton instance
places_provider = PlacesProvider()
