import asyncio
import time
from typing import Dict, List, Optional, Any
import httpx

# Public Overpass API mirrors ordered by speed and reliability
OVERPASS_ENDPOINTS = [
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://z.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]

# Category mapping from OpenStreetMap tags to canonical Explore categories
OSM_CATEGORY_MAP = {
    # Attractions
    "attraction": "attraction",
    "viewpoint": "attraction",
    "monument": "historic",
    "memorial": "historic",
    "castle": "historic",
    "fort": "historic",
    "ruins": "historic",
    "palace": "historic",
    "archaeological_site": "historic",
    "heritage": "historic",
    "artwork": "attraction",
    "theme_park": "activity",
    "zoo": "activity",
    "aquarium": "activity",
    # Museums
    "museum": "museum",
    "gallery": "museum",
    # Stays / Accommodations
    "hotel": "hotel",
    "hostel": "hotel",
    "guest_house": "hotel",
    "motel": "hotel",
    "resort": "hotel",
    "apartment": "hotel",
    # Dining / Food
    "restaurant": "restaurant",
    "fast_food": "restaurant",
    "food_court": "restaurant",
    "pub": "restaurant",
    "bar": "restaurant",
    # Cafes
    "cafe": "cafe",
    "bakery": "cafe",
    "ice_cream": "cafe",
    # Parks / Nature
    "park": "park",
    "garden": "park",
    "nature_reserve": "park",
    "pitch": "activity",
    "water_park": "activity",
    "sports_centre": "activity",
}


class OverpassService:
    """
    Service for querying OpenStreetMap elements via the Overpass API.
    Provides 100% dynamic worldwide place discovery.
    """

    def __init__(self):
        self.headers = {
            "User-Agent": "TravelTrack-App/4.0 (https://triptrack-frontend.onrender.com; contact: info@triptrack.app)",
            "Accept": "application/json",
        }
        self.timeout = httpx.Timeout(1.8, connect=0.8)
        self._cache: Dict[str, tuple[float, List[Dict[str, Any]]]] = {}
        self.cache_ttl = 86400  # 24 hours

    def _get_cache(self, key: str) -> Optional[List[Dict[str, Any]]]:
        if key in self._cache:
            ts, val = self._cache[key]
            if time.time() - ts < self.cache_ttl and len(val) > 0:
                return val
        return None

    def _set_cache(self, key: str, val: List[Dict[str, Any]]):
        if val and len(val) > 0:
            self._cache[key] = (time.time(), val)

    def _map_osm_category(self, tags: Dict[str, str]) -> str:
        """
        Determine the canonical TravelTrack category from OSM tags.
        """
        if "tourism" in tags and tags["tourism"] in OSM_CATEGORY_MAP:
            return OSM_CATEGORY_MAP[tags["tourism"]]
        if "historic" in tags and tags["historic"] in OSM_CATEGORY_MAP:
            return OSM_CATEGORY_MAP[tags["historic"]]
        if "amenity" in tags and tags["amenity"] in OSM_CATEGORY_MAP:
            return OSM_CATEGORY_MAP[tags["amenity"]]
        if "leisure" in tags and tags["leisure"] in OSM_CATEGORY_MAP:
            return OSM_CATEGORY_MAP[tags["leisure"]]
        if "shop" in tags and tags["shop"] in ["bakery", "pastry", "coffee", "tea"]:
            return "cafe"
        return "attraction"

    def _format_address(self, tags: Dict[str, str], name: str) -> str:
        """
        Format a readable address string from OSM address tags.
        """
        parts = []
        street = tags.get("addr:street")
        housenumber = tags.get("addr:housenumber")
        if housenumber and street:
            parts.append(f"{housenumber} {street}")
        elif street:
            parts.append(street)

        suburb = tags.get("addr:suburb") or tags.get("addr:district") or tags.get("addr:neighbourhood")
        if suburb:
            parts.append(suburb)

        city = tags.get("addr:city") or tags.get("addr:town") or tags.get("addr:village")
        if city:
            parts.append(city)

        state = tags.get("addr:state")
        if state:
            parts.append(state)

        postcode = tags.get("addr:postcode")
        if postcode:
            parts.append(postcode)

        country = tags.get("addr:country")
        if country:
            parts.append(country)

        return ", ".join(parts) if parts else name

    def _build_overpass_query(self, lat: float, lon: float, category: str, radius: int) -> str:
        """
        Construct an optimized Overpass QL query string for the requested category.
        """
        cat_lower = category.lower().strip()

        if cat_lower == "hotels":
            body = f"""
  node["tourism"~"hotel|hostel|guest_house|resort"](around:{radius},{lat},{lon});
  way["tourism"~"hotel|hostel|guest_house|resort"](around:{radius},{lat},{lon});
"""
        elif cat_lower in ["restaurants", "dining"]:
            body = f"""
  node["amenity"~"restaurant|fast_food|pub"](around:{radius},{lat},{lon});
  way["amenity"~"restaurant|fast_food|pub"](around:{radius},{lat},{lon});
"""
        elif cat_lower == "cafes":
            body = f"""
  node["amenity"="cafe"](around:{radius},{lat},{lon});
  node["shop"~"bakery|coffee"](around:{radius},{lat},{lon});
"""
        elif cat_lower == "museums":
            body = f"""
  node["tourism"~"museum|gallery"](around:{radius},{lat},{lon});
  way["tourism"~"museum|gallery"](around:{radius},{lat},{lon});
"""
        elif cat_lower == "parks":
            body = f"""
  node["leisure"~"park|garden|nature_reserve"](around:{radius},{lat},{lon});
  way["leisure"~"park|garden|nature_reserve"](around:{radius},{lat},{lon});
"""
        elif cat_lower == "historic":
            body = f"""
  node["historic"~"monument|memorial|castle|fort|ruins|palace|archaeological_site|heritage"](around:{radius},{lat},{lon});
  way["historic"~"monument|memorial|castle|fort|ruins|palace|archaeological_site|heritage"](around:{radius},{lat},{lon});
"""
        elif cat_lower == "activities":
            body = f"""
  node["tourism"~"theme_park|zoo|aquarium|water_park"](around:{radius},{lat},{lon});
  way["tourism"~"theme_park|zoo|aquarium|water_park"](around:{radius},{lat},{lon});
  node["leisure"~"water_park|sports_centre"](around:{radius},{lat},{lon});
"""
        elif cat_lower == "attractions":
            body = f"""
  node["tourism"~"attraction|museum|gallery|theme_park|zoo|aquarium|viewpoint"](around:{radius},{lat},{lon});
  way["tourism"~"attraction|museum|gallery|theme_park|zoo|aquarium|viewpoint"](around:{radius},{lat},{lon});
  node["historic"~"monument|memorial|castle|fort|ruins|palace|heritage"](around:{radius},{lat},{lon});
  way["historic"~"monument|memorial|castle|fort|ruins|palace|heritage"](around:{radius},{lat},{lon});
"""
        else:  # "all"
            body = f"""
  node["tourism"~"attraction|museum|viewpoint|hotel|resort"](around:{radius},{lat},{lon});
  way["tourism"~"attraction|museum|viewpoint|hotel|resort"](around:{radius},{lat},{lon});
  node["historic"~"monument|memorial|castle|fort|palace|heritage"](around:{radius},{lat},{lon});
  way["historic"~"monument|memorial|castle|fort|palace|heritage"](around:{radius},{lat},{lon});
  node["amenity"~"restaurant|cafe"](around:{radius},{lat},{lon});
  node["leisure"~"park|garden"](around:{radius},{lat},{lon});
"""

        query = f"""[out:json][timeout:3];
(
{body}
);
out center tags 30;
"""
        return query

    async def _query_single_endpoint(self, client: httpx.AsyncClient, endpoint: str, query: str) -> List[Dict[str, Any]]:
        try:
            res = await client.post(endpoint, data={"data": query}, headers=self.headers)
            if res.status_code == 200:
                data = res.json()
                return data.get("elements", [])
        except Exception:
            pass
        return []

    async def discover_places(
        self,
        lat: float,
        lon: float,
        category: str = "all",
        radius: int = 6000
    ) -> List[Dict[str, Any]]:
        """
        Query Overpass API around given coordinates and return deduplicated, normalized place items.
        Queries live mirrors sequentially with fast failover.
        """
        cache_key = f"overpass:{round(lat, 3)}:{round(lon, 3)}:{category.lower()}"
        cached = self._get_cache(cache_key)
        if cached is not None and len(cached) > 0:
            return cached

        query = self._build_overpass_query(lat, lon, category, radius)
        elements = []

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for ep in OVERPASS_ENDPOINTS[:2]:
                try:
                    res_elements = await self._query_single_endpoint(client, ep, query)
                    if res_elements:
                        elements = res_elements
                        break
                except Exception:
                    continue

        # Parse, filter, and deduplicate
        seen_names = set()
        seen_ids = set()
        parsed_places: List[Dict[str, Any]] = []

        for el in elements:
            tags = el.get("tags", {})
            name = tags.get("name:en") or tags.get("name") or tags.get("int_name")
            if not name or len(name.strip()) < 2:
                continue

            name_clean = name.strip()
            norm_name = name_clean.lower()

            if norm_name in seen_names:
                continue

            el_type = el.get("type", "node")
            el_id = el.get("id")
            canonical_id = f"osm_{el_type}_{el_id}"

            if canonical_id in seen_ids:
                continue

            p_lat = el.get("lat") or el.get("center", {}).get("lat")
            p_lon = el.get("lon") or el.get("center", {}).get("lon")

            if p_lat is None or p_lon is None:
                continue

            mapped_category = self._map_osm_category(tags)
            address = self._format_address(tags, name_clean)

            phone = tags.get("phone") or tags.get("contact:phone")
            website = tags.get("website") or tags.get("contact:website") or tags.get("url")
            opening_hours = tags.get("opening_hours")
            osm_wikipedia = tags.get("wikipedia") or tags.get("wikipedia:en")
            osm_wikidata = tags.get("wikidata")
            osm_image = tags.get("image") or tags.get("wikimedia_commons")

            tags_list = []
            if "cuisine" in tags:
                tags_list.extend([c.strip().title() for c in tags["cuisine"].split(";") if c.strip()])
            if "stars" in tags:
                tags_list.append(f"{tags['stars']} Stars")
            if "heritage" in tags or "historic" in tags:
                tags_list.append("Heritage")
            if "tourism" in tags:
                tags_list.append(tags["tourism"].replace("_", " ").title())

            seen_names.add(norm_name)
            seen_ids.add(canonical_id)

            parsed_places.append({
                "id": canonical_id,
                "provider_id": f"{el_type}/{el_id}",
                "name": name_clean,
                "category": mapped_category,
                "address": address,
                "lat": float(p_lat),
                "lon": float(p_lon),
                "phone": phone,
                "website": website,
                "opening_hours": opening_hours,
                "osm_wikipedia": osm_wikipedia,
                "osm_wikidata": osm_wikidata,
                "osm_image": osm_image,
                "tags": tags_list[:4]
            })

        if parsed_places:
            self._set_cache(cache_key, parsed_places)
        return parsed_places

    async def fetch_entity_by_osm_id(self, el_type: str, el_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch full details for an exact OSM entity (node, way, or relation) by its ID.
        """
        el_type_clean = el_type.lower()
        if el_type_clean not in ["node", "way", "relation"]:
            el_type_clean = "node"

        cache_key = f"osm_entity:{el_type_clean}:{el_id}"
        cached = self._get_cache(cache_key)
        if cached is not None and isinstance(cached, list) and len(cached) > 0:
            return cached[0]

        query = f"[out:json][timeout:3];{el_type_clean}({el_id});out center tags;"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for ep in OVERPASS_ENDPOINTS:
                try:
                    elements = await self._query_single_endpoint(client, ep, query)
                    if elements:
                        el = elements[0]
                        tags = el.get("tags", {})
                        name = tags.get("name:en") or tags.get("name") or tags.get("int_name") or f"Place {el_id}"
                        p_lat = el.get("lat") or el.get("center", {}).get("lat")
                        p_lon = el.get("lon") or el.get("center", {}).get("lon")
                        if p_lat is None or p_lon is None:
                            continue

                        canonical_id = f"osm_{el_type_clean}_{el_id}"
                        mapped_category = self._map_osm_category(tags)
                        address = self._format_address(tags, name)

                        res = {
                            "id": canonical_id,
                            "provider_id": f"{el_type_clean}/{el_id}",
                            "name": name,
                            "category": mapped_category,
                            "address": address,
                            "lat": float(p_lat),
                            "lon": float(p_lon),
                            "phone": tags.get("phone") or tags.get("contact:phone"),
                            "website": tags.get("website") or tags.get("contact:website") or tags.get("url"),
                            "opening_hours": tags.get("opening_hours"),
                            "osm_wikipedia": tags.get("wikipedia") or tags.get("wikipedia:en"),
                            "osm_wikidata": tags.get("wikidata"),
                            "osm_image": tags.get("image") or tags.get("wikimedia_commons"),
                            "tags": []
                        }
                        self._set_cache(cache_key, [res])
                        return res
                except Exception:
                    continue

        return None


# Singleton instance
overpass_service = OverpassService()
