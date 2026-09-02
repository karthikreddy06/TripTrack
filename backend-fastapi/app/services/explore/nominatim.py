import time
import urllib.parse
from typing import Dict, Optional, Any, List
import httpx

# In-memory cache for dynamic geocoding results (TTL: 24 hours)
_GEO_CACHE: Dict[str, Dict[str, Any]] = {}
GEO_CACHE_TTL = 86400

DESTINATION_CITY_TYPES = {
    "city", "town", "village", "hamlet", "municipality", "administrative",
    "suburb", "neighbourhood", "quarter", "borough", "city_district",
    "district", "county", "state", "province", "region", "country", "island"
}

LANDMARK_TYPES = {
    "monument", "memorial", "castle", "fort", "ruins", "palace", "tower",
    "attraction", "museum", "gallery", "hotel", "hostel", "motel", "resort",
    "restaurant", "fast_food", "food_court", "pub", "bar", "cafe", "bakery",
    "park", "garden", "nature_reserve", "theme_park", "zoo", "aquarium",
    "archaeological_site", "viewpoint", "artwork", "place_of_worship", "building"
}


class NominatimService:
    """
    OpenStreetMap Nominatim Geocoding Service.
    100% dynamic, global geocoding for arbitrary cities, towns, landmarks, and venues worldwide.
    No hardcoded cities, whitelist, or fixed databases.
    """

    def __init__(self):
        self.timeout = httpx.Timeout(6.5, connect=3.0)
        self.headers = {
            "User-Agent": "TravelTrack-Explore/4.0 (https://triptrack-frontend.onrender.com; contact: info@triptrack.app)",
            "Accept": "application/json"
        }

    def _get_cache(self, key: str) -> Optional[Dict[str, Any]]:
        cached = _GEO_CACHE.get(key)
        if cached and (time.time() - cached["timestamp"]) < GEO_CACHE_TTL:
            return cached["data"]
        return None

    def _set_cache(self, key: str, data: Optional[Dict[str, Any]]):
        _GEO_CACHE[key] = {
            "timestamp": time.time(),
            "data": data
        }

    def _classify_entity(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify a Nominatim result into a destination or a specific place.
        """
        osm_type = item.get("osm_type", "node")  # 'node', 'way', 'relation'
        osm_id = item.get("osm_id", "")
        item_class = item.get("class", "place")
        item_type = item.get("type", "city")
        display_name = item.get("display_name", "")
        address = item.get("address", {})
        extratags = item.get("extratags", {}) or {}
        namedetails = item.get("namedetails", {}) or {}

        # Prioritize English/International Romanized name when available
        name = (
            namedetails.get("name:en")
            or namedetails.get("int_name")
            or item.get("name")
            or address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("tourism")
            or address.get("historic")
            or address.get("amenity")
            or display_name.split(",")[0].strip()
        )

        country = address.get("country", "")
        city = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("county")
            or address.get("state")
            or name
        )

        # Determine if entity is a Destination (City/Town/Country) vs a Specific Place/Landmark
        is_landmark = (
            item_type in LANDMARK_TYPES
            or item_class in {"tourism", "historic", "amenity", "leisure", "shop", "building"}
        )

        is_destination = (
            (item_type in DESTINATION_CITY_TYPES or (item_class == "boundary" and item_type == "administrative"))
            and not is_landmark
        )

        # Map to canonical TravelTrack category
        category = "attraction"
        if is_destination:
            category = "destination"
        elif item_class == "historic" or item_type in ["monument", "memorial", "castle", "fort", "ruins", "palace", "archaeological_site"]:
            category = "historic"
        elif item_type in ["museum", "gallery"]:
            category = "museum"
        elif item_type in ["hotel", "hostel", "motel", "guest_house", "resort"]:
            category = "hotel"
        elif item_type in ["restaurant", "fast_food", "food_court", "pub", "bar"]:
            category = "restaurant"
        elif item_type in ["cafe", "bakery"]:
            category = "cafe"
        elif item_type in ["park", "garden", "nature_reserve"]:
            category = "park"
        elif item_type in ["theme_park", "zoo", "aquarium", "water_park"]:
            category = "activity"

        lat = float(item.get("lat", 0.0))
        lon = float(item.get("lon", 0.0))
        raw_bbox = item.get("boundingbox", [lat - 0.1, lat + 0.1, lon - 0.1, lon + 0.1])
        bbox = [float(b) for b in raw_bbox]

        place_id = f"osm_{osm_type}_{osm_id}" if osm_id else f"geo_{round(lat, 4)}_{round(lon, 4)}"

        return {
            "id": place_id,
            "place_id": place_id,
            "provider_id": f"{osm_type}/{osm_id}" if osm_id else "",
            "osm_type": osm_type,
            "osm_id": str(osm_id),
            "name": name,
            "display_name": display_name,
            "city": city,
            "country": country,
            "lat": lat,
            "lon": lon,
            "boundingbox": bbox,
            "is_destination": is_destination,
            "category": category,
            "osm_class": item_class,
            "osm_type_tag": item_type,
            "osm_wikipedia": extratags.get("wikipedia") or namedetails.get("wikipedia"),
            "osm_wikidata": extratags.get("wikidata") or namedetails.get("wikidata"),
            "osm_image": extratags.get("image"),
            "phone": extratags.get("phone") or extratags.get("contact:phone"),
            "website": extratags.get("website") or extratags.get("contact:website"),
            "opening_hours": extratags.get("opening_hours"),
            "address": address,
            "importance": float(item.get("importance", 0.5)),
        }

    async def geocode(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Geocode any arbitrary search query worldwide.
        Returns classified entity (destination or place) with exact coordinates.
        """
        if not query or not query.strip():
            return None

        clean_q = query.strip()
        norm_key = f"geocode:{clean_q.lower()}"

        cached = self._get_cache(norm_key)
        if cached is not None:
            return cached

        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": clean_q,
            "format": "jsonv2",
            "addressdetails": 1,
            "extratags": 1,
            "namedetails": 1,
            "limit": 5
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url, params=params, headers=self.headers)
                if res.status_code == 200:
                    data = res.json()
                    if isinstance(data, list) and len(data) > 0:
                        classified = self._classify_entity(data[0])
                        self._set_cache(norm_key, classified)
                        return classified
        except Exception:
            pass

        return None

    async def geocode_destination(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Convenience method for destination geocoding.
        """
        return await self.geocode(query)

    async def lookup_by_osm_id(self, osm_type: str, osm_id: str) -> Optional[Dict[str, Any]]:
        """
        Directly resolve an OSM entity by its type (node/way/relation) and ID.
        """
        prefix_map = {"node": "N", "way": "W", "relation": "R"}
        prefix = prefix_map.get(osm_type.lower(), "N")
        osm_key = f"{prefix}{osm_id}"
        cache_key = f"lookup:{osm_key}"

        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        url = "https://nominatim.openstreetmap.org/lookup"
        params = {
            "osm_ids": osm_key,
            "format": "jsonv2",
            "addressdetails": 1,
            "extratags": 1,
            "namedetails": 1
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url, params=params, headers=self.headers)
                if res.status_code == 200:
                    data = res.json()
                    if isinstance(data, list) and len(data) > 0:
                        classified = self._classify_entity(data[0])
                        self._set_cache(cache_key, classified)
                        return classified
        except Exception:
            pass

        return None

    async def search_pois_in_area(self, city_name: str, category: str = "all", limit: int = 25) -> List[Dict[str, Any]]:
        """
        Discover notable POIs in an area via Nominatim search.
        Serves as a robust fallback when Overpass is slow or empty.
        """
        if not city_name:
            return []

        search_terms = ["attractions", "historic", "museums", "hotels", "restaurants"]
        cat_lower = category.lower().strip()
        if cat_lower in ["hotels", "hotel"]:
            search_terms = ["hotels"]
        elif cat_lower in ["restaurants", "restaurant", "dining"]:
            search_terms = ["restaurants"]
        elif cat_lower in ["cafes", "cafe"]:
            search_terms = ["cafes"]
        elif cat_lower in ["museums", "museum"]:
            search_terms = ["museums"]
        elif cat_lower in ["parks", "park"]:
            search_terms = ["parks"]

        results: List[Dict[str, Any]] = []
        seen_names = set()

        url = "https://nominatim.openstreetmap.org/search"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for term in search_terms[:3]:
                try:
                    params = {
                        "q": f"{term} in {city_name}",
                        "format": "jsonv2",
                        "addressdetails": 1,
                        "extratags": 1,
                        "namedetails": 1,
                        "limit": 15
                    }
                    res = await client.get(url, params=params, headers=self.headers)
                    if res.status_code == 200:
                        data = res.json()
                        if isinstance(data, list):
                            for item in data:
                                classified = self._classify_entity(item)
                                if not classified["is_destination"]:
                                    norm_name = classified["name"].lower()
                                    if norm_name not in seen_names:
                                        seen_names.add(norm_name)
                                        results.append({
                                            "id": classified["id"],
                                            "provider_id": classified["provider_id"],
                                            "name": classified["name"],
                                            "category": classified["category"],
                                            "address": classified["display_name"],
                                            "lat": classified["lat"],
                                            "lon": classified["lon"],
                                            "phone": classified.get("phone"),
                                            "website": classified.get("website"),
                                            "opening_hours": classified.get("opening_hours"),
                                            "osm_wikipedia": classified.get("osm_wikipedia"),
                                            "osm_wikidata": classified.get("osm_wikidata"),
                                            "osm_image": classified.get("osm_image"),
                                            "tags": [classified.get("osm_type_tag", "Place").title()]
                                        })
                except Exception:
                    pass

        return results[:limit]


# Singleton instance
nominatim_service = NominatimService()
