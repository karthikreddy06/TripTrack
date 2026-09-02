import asyncio
import math
import time
from typing import Dict, Optional, Any, List
import httpx

# In-memory cache for dynamic geocoding & suggestions (TTL: 24 hours)
_GEO_CACHE: Dict[str, Dict[str, Any]] = {}
_SUGGESTION_CACHE: Dict[str, List[Dict[str, Any]]] = {}
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


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points in kilometers.
    """
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class NominatimService:
    """
    OpenStreetMap Nominatim Geocoding and Autocomplete Suggestion Service.
    100% dynamic, global geocoding for arbitrary cities, towns, landmarks, and venues worldwide.
    Built-in typo tolerance, fuzzy matching, and zero hardcoded city lists.
    """

    def __init__(self):
        self.timeout = httpx.Timeout(4.0, connect=1.8)
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
        if data:
            _GEO_CACHE[key] = {
                "timestamp": time.time(),
                "data": data
            }

    def _classify_entity(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify a Nominatim result into a destination or a specific place.
        """
        osm_type = item.get("osm_type", "node")
        osm_id = item.get("osm_id", "")
        item_class = item.get("class", "place")
        item_type = item.get("type", "city")
        display_name = item.get("display_name", "")
        address = item.get("address", {}) or {}
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

    async def get_suggestions(self, query: str, limit: int = 6) -> List[Dict[str, Any]]:
        """
        Typo-tolerant autocomplete suggestions powered by Photon OSM and Wikipedia Opensearch.
        Zero hardcoded lists. Returns structured items with name, subtitle, coordinates, and classification.
        """
        q = query.strip()
        if not q or len(q) < 2:
            return []

        cache_key = f"sug:{q.lower()}"
        if cache_key in _SUGGESTION_CACHE:
            return _SUGGESTION_CACHE[cache_key][:limit]

        suggestions: List[Dict[str, Any]] = []
        seen = set()

        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                r_photon, r_wiki = await asyncio.gather(
                    client.get("https://photon.komoot.io/api/", params={"q": q, "limit": 8}),
                    client.get("https://en.wikipedia.org/w/api.php", params={"action": "opensearch", "search": q, "limit": 4, "namespace": 0, "format": "json"}),
                    return_exceptions=True
                )

                # 1. Process Photon results
                if not isinstance(r_photon, Exception) and r_photon.status_code == 200:
                    for feat in r_photon.json().get("features", []):
                        props = feat.get("properties", {})
                        name = props.get("name")
                        if not name:
                            continue
                        state = props.get("state") or props.get("district") or ""
                        country = props.get("country") or ""
                        osm_type = props.get("type") or props.get("osm_value") or "place"
                        coords = feat.get("geometry", {}).get("coordinates", [0, 0])
                        is_dest = osm_type in DESTINATION_CITY_TYPES

                        imp = 0.4
                        if is_dest:
                            if osm_type in ["city", "country"]:
                                imp = 0.95
                            elif osm_type in ["town", "municipality", "state", "region"]:
                                imp = 0.8
                            elif osm_type in ["suburb", "neighbourhood", "quarter", "borough"]:
                                imp = 0.6
                            else:
                                imp = 0.35

                        key = f"{name.lower()}:{state.lower()}:{country.lower()}"
                        if key not in seen:
                            seen.add(key)
                            sub_parts = [p for p in [state, country] if p and p.lower() != name.lower()]
                            suggestions.append({
                                "id": f"osm_{props.get('osm_type', 'N')}_{props.get('osm_id', '')}",
                                "place_id": f"osm_{props.get('osm_type', 'N')}_{props.get('osm_id', '')}",
                                "provider_id": f"{props.get('osm_type', 'N')}/{props.get('osm_id', '')}",
                                "name": name,
                                "display_name": f"{name}, {', '.join(sub_parts)}" if sub_parts else name,
                                "city": props.get("city") or name,
                                "state": state,
                                "country": country,
                                "lat": float(coords[1]),
                                "lon": float(coords[0]),
                                "boundingbox": [coords[1] - 0.1, coords[1] + 0.1, coords[0] - 0.1, coords[0] + 0.1],
                                "is_destination": is_dest,
                                "category": "destination" if is_dest else "place",
                                "subtitle": ", ".join(sub_parts) if sub_parts else country,
                                "type": osm_type,
                                "importance": imp
                            })

                # 2. Check Wikipedia typo corrections if needed
                has_major_dest = any(s["is_destination"] and s.get("importance", 0) >= 0.8 for s in suggestions)
                if (len(suggestions) < 3 or not has_major_dest) and not isinstance(r_wiki, Exception) and r_wiki.status_code == 200:
                    wiki_titles = r_wiki.json()[1] if len(r_wiki.json()) > 1 else []
                    for title in wiki_titles[:2]:
                        if any(s["name"].lower() == title.lower() for s in suggestions):
                            continue
                        try:
                            r_corr = await client.get("https://photon.komoot.io/api/", params={"q": title, "limit": 2})
                            if r_corr.status_code == 200:
                                for feat in r_corr.json().get("features", []):
                                    props = feat.get("properties", {})
                                    name = props.get("name") or title
                                    state = props.get("state") or props.get("district") or ""
                                    country = props.get("country") or ""
                                    osm_type = props.get("type") or props.get("osm_value") or "place"
                                    coords = feat.get("geometry", {}).get("coordinates", [0, 0])
                                    is_dest = osm_type in DESTINATION_CITY_TYPES
                                    imp = 0.5
                                    if is_dest:
                                        if osm_type in ["city", "country"]:
                                            imp = 0.98
                                        elif osm_type in ["town", "municipality", "state", "region"]:
                                            imp = 0.85
                                        elif osm_type in ["suburb", "neighbourhood", "quarter", "borough"]:
                                            imp = 0.65
                                        else:
                                            imp = 0.4

                                    key = f"{name.lower()}:{state.lower()}:{country.lower()}"
                                    if key not in seen:
                                        seen.add(key)
                                        sub_parts = [p for p in [state, country] if p and p.lower() != name.lower()]
                                        suggestions.append({
                                            "id": f"osm_{props.get('osm_type', 'N')}_{props.get('osm_id', '')}",
                                            "place_id": f"osm_{props.get('osm_type', 'N')}_{props.get('osm_id', '')}",
                                            "provider_id": f"{props.get('osm_type', 'N')}/{props.get('osm_id', '')}",
                                            "name": name,
                                            "display_name": f"{name}, {', '.join(sub_parts)}" if sub_parts else name,
                                            "city": props.get("city") or name,
                                            "state": state,
                                            "country": country,
                                            "lat": float(coords[1]),
                                            "lon": float(coords[0]),
                                            "boundingbox": [coords[1] - 0.1, coords[1] + 0.1, coords[0] - 0.1, coords[0] - 0.1],
                                            "is_destination": is_dest,
                                            "category": "destination" if is_dest else "place",
                                            "subtitle": ", ".join(sub_parts) if sub_parts else country,
                                            "type": osm_type,
                                            "importance": imp
                                        })
                        except Exception:
                            pass

        except Exception:
            pass

        suggestions.sort(key=lambda s: (s["is_destination"], s.get("importance", 0.0)), reverse=True)
        result = suggestions[:limit]
        if result:
            _SUGGESTION_CACHE[cache_key] = result
        return result

    async def geocode(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Geocode any arbitrary search query worldwide.
        Includes automatic typo tolerance and fuzzy fallback.
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
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                res = await client.get(url, params=params)
                if res.status_code == 200:
                    data = res.json()
                    if isinstance(data, list) and len(data) > 0:
                        # Sort candidates strictly by OpenStreetMap global prominence/importance
                        data.sort(
                            key=lambda c: float(c.get("importance", 0.0) or 0.0),
                            reverse=True
                        )
                        best_match = data[0]
                        classified = self._classify_entity(best_match)
                        
                        # Is best_match a major landmark (e.g. Charminar, Eiffel Tower) or a primary destination?
                        is_major_entity = float(best_match.get("importance", 0.0) or 0.0) >= 0.55
                        clean_name = classified["name"].lower()
                        clean_q_lower = clean_q.lower()
                        is_name_exact = clean_q_lower == clean_name

                        if not is_major_entity and not is_name_exact:
                            # Check if suggestions resolved a major canonical destination or landmark
                            # (e.g. kolkota -> Kolkata, banglore -> Bengaluru, pariss -> Paris, hyderbad -> Hyderabad)
                            sugs = await self.get_suggestions(clean_q, limit=3)
                            for sug in sugs:
                                if sug.get("importance", 0) > float(best_match.get("importance", 0.0) or 0.0):
                                    self._set_cache(norm_key, sug)
                                    return sug

                        self._set_cache(norm_key, classified)
                        return classified

                # If direct Nominatim query returned empty, try typo resolution via suggestions
                sugs = await self.get_suggestions(clean_q, limit=2)
                if sugs:
                    top_sug = sugs[0]
                    self._set_cache(norm_key, top_sug)
                    return top_sug

        except Exception:
            pass

        return None

    async def geocode_destination(self, query: str) -> Optional[Dict[str, Any]]:
        return await self.geocode(query)

    async def lookup_by_osm_id(self, osm_type: str, osm_id: str) -> Optional[Dict[str, Any]]:
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
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                res = await client.get(url, params=params)
                if res.status_code == 200:
                    data = res.json()
                    if isinstance(data, list) and len(data) > 0:
                        classified = self._classify_entity(data[0])
                        self._set_cache(cache_key, classified)
                        return classified
        except Exception:
            pass

        return None

    async def search_pois_in_area(self, city_name: str, category: str = "all", limit: int = 20) -> List[Dict[str, Any]]:
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
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            for term in search_terms[:2]:
                try:
                    params = {
                        "q": f"{term} in {city_name}",
                        "format": "jsonv2",
                        "addressdetails": 1,
                        "extratags": 1,
                        "namedetails": 1,
                        "limit": 15
                    }
                    res = await client.get(url, params=params)
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
