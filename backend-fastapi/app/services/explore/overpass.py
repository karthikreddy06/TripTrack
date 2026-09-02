import time
import urllib.parse
from typing import Dict, List, Optional, Any
import httpx

# In-memory cache for Overpass API query results (TTL: 12 hours)
_OVERPASS_CACHE: Dict[str, Dict[str, Any]] = {}
OVERPASS_CACHE_TTL = 43200

# Public Overpass mirror endpoints with automatic failover
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter"
]


class OverpassService:
    """
    OpenStreetMap Overpass API Service.
    Discovers 20-50+ real-world travel destinations, attractions, dining, cafes, and accommodations.
    """

    def __init__(self):
        self.timeout = httpx.Timeout(12.0, connect=4.0)
        self.headers = {
            "User-Agent": "TravelTrack-Explore/3.0 (https://triptrack-frontend.onrender.com; contact: info@triptrack.app)"
        }

    def _get_cache(self, key: str) -> Optional[List[Dict[str, Any]]]:
        cached = _OVERPASS_CACHE.get(key)
        if cached and (time.time() - cached["timestamp"]) < OVERPASS_CACHE_TTL:
            return cached["data"]
        return None

    def _set_cache(self, key: str, data: List[Dict[str, Any]]):
        _OVERPASS_CACHE[key] = {
            "timestamp": time.time(),
            "data": data
        }

    def _map_osm_category(self, tags: Dict[str, str]) -> str:
        """Categorize an OSM element into a TravelTrack category."""
        tourism = tags.get("tourism", "").lower()
        amenity = tags.get("amenity", "").lower()
        historic = tags.get("historic", "").lower()
        leisure = tags.get("leisure", "").lower()

        if tourism in ["hotel", "hostel", "guest_house", "motel", "resort", "alpine_hut", "apartment"]:
            return "hotel"
        if amenity in ["restaurant", "food_court"]:
            return "restaurant"
        if amenity in ["cafe", "bakery", "bar", "pub"]:
            return "cafe"
        if tourism in ["museum", "gallery"]:
            return "museum"
        if leisure in ["park", "nature_reserve", "garden"]:
            return "park"
        if historic or tourism in ["monument", "memorial", "castle", "fort", "ruins", "archaeological_site", "palace"]:
            return "historic"
        if tourism in ["theme_park", "zoo", "aquarium", "water_park"] or leisure in ["sports_centre", "ice_rink", "water_park"]:
            return "activity"
        if tourism in ["attraction", "viewpoint", "artwork"] or amenity in ["place_of_worship"]:
            return "attraction"

        return "attraction"

    def _format_address(self, tags: Dict[str, str], fallback_name: str = "") -> str:
        """Build a clean human-readable address from OSM address tags."""
        addr_parts = []
        if tags.get("addr:housenumber"):
            addr_parts.append(tags["addr:housenumber"])
        if tags.get("addr:street"):
            addr_parts.append(tags["addr:street"])
        if tags.get("addr:suburb"):
            addr_parts.append(tags["addr:suburb"])
        if tags.get("addr:district"):
            addr_parts.append(tags["addr:district"])
        if tags.get("addr:city"):
            addr_parts.append(tags["addr:city"])
        elif tags.get("addr:town"):
            addr_parts.append(tags["addr:town"])
        if tags.get("addr:postcode"):
            addr_parts.append(tags["addr:postcode"])
        if tags.get("addr:state"):
            addr_parts.append(tags["addr:state"])

        if addr_parts:
            return ", ".join(addr_parts)
        return tags.get("address") or tags.get("location") or fallback_name

    def _build_overpass_query(self, lat: float, lon: float, category: str = "all", radius: int = 15000) -> str:
        """Construct an optimized Overpass QL query string."""
        cat_lower = category.lower().strip()

        if cat_lower == "hotels":
            body = f"""
  node["tourism"~"hotel|hostel|resort|guest_house|motel"](around:{radius},{lat},{lon});
  way["tourism"~"hotel|hostel|resort|guest_house|motel"](around:{radius},{lat},{lon});
"""
        elif cat_lower == "restaurants":
            body = f"""
  node["amenity"~"restaurant|food_court"](around:{radius},{lat},{lon});
  way["amenity"~"restaurant|food_court"](around:{radius},{lat},{lon});
"""
        elif cat_lower == "cafes":
            body = f"""
  node["amenity"~"cafe|bakery"](around:{radius},{lat},{lon});
  way["amenity"~"cafe|bakery"](around:{radius},{lat},{lon});
"""
        elif cat_lower == "museums":
            body = f"""
  node["tourism"~"museum|gallery"](around:{radius},{lat},{lon});
  way["tourism"~"museum|gallery"](around:{radius},{lat},{lon});
  node["historic"~"archaeological_site|museum"](around:{radius},{lat},{lon});
  way["historic"~"archaeological_site|museum"](around:{radius},{lat},{lon});
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
  node["leisure"~"water_park|sports_centre|ice_rink"](around:{radius},{lat},{lon});
"""
        elif cat_lower == "attractions":
            body = f"""
  node["tourism"~"attraction|museum|gallery|theme_park|zoo|aquarium|viewpoint"](around:{radius},{lat},{lon});
  way["tourism"~"attraction|museum|gallery|theme_park|zoo|aquarium|viewpoint"](around:{radius},{lat},{lon});
  node["historic"~"monument|memorial|castle|fort|ruins|palace|heritage"](around:{radius},{lat},{lon});
  way["historic"~"monument|memorial|castle|fort|ruins|palace|heritage"](around:{radius},{lat},{lon});
"""
        else: # "all"
            body = f"""
  node["tourism"~"attraction|museum|gallery|theme_park|zoo|aquarium|viewpoint|hotel|hostel|resort"](around:{radius},{lat},{lon});
  way["tourism"~"attraction|museum|gallery|theme_park|zoo|aquarium|viewpoint|hotel|hostel|resort"](around:{radius},{lat},{lon});
  node["historic"~"monument|memorial|castle|fort|ruins|palace|heritage"](around:{radius},{lat},{lon});
  way["historic"~"monument|memorial|castle|fort|ruins|palace|heritage"](around:{radius},{lat},{lon});
  node["amenity"~"restaurant|cafe"](around:{radius},{lat},{lon});
  node["leisure"~"park|garden"](around:{radius},{lat},{lon});
"""

        query = f"""[out:json][timeout:12];
(
{body}
);
out center tags 80;
"""
        return query

    async def discover_places(
        self,
        lat: float,
        lon: float,
        category: str = "all",
        radius: int = 15000
    ) -> List[Dict[str, Any]]:
        """
        Query Overpass API around given coordinates and return deduplicated, normalized place items.
        """
        cache_key = f"overpass:{round(lat, 3)}:{round(lon, 3)}:{category.lower()}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        query = self._build_overpass_query(lat, lon, category, radius)
        elements = []

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for endpoint in OVERPASS_ENDPOINTS:
                try:
                    res = await client.post(
                        endpoint,
                        data={"data": query},
                        headers=self.headers
                    )
                    if res.status_code == 200:
                        data = res.json()
                        elements = data.get("elements", [])
                        if elements:
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
            full_id = f"osm_{el_type}_{el_id}"
            if full_id in seen_ids:
                continue

            # Extract Coordinates
            p_lat = el.get("lat") or el.get("center", {}).get("lat")
            p_lon = el.get("lon") or el.get("center", {}).get("lon")
            if p_lat is None or p_lon is None:
                continue

            cat = self._map_osm_category(tags)
            address = self._format_address(tags, name_clean)

            # Wikipedia / Wikidata metadata
            wiki_tag = tags.get("wikipedia") or tags.get("wikipedia:en")
            wikidata_tag = tags.get("wikidata")
            img_tag = tags.get("image") or tags.get("wikimedia_commons")

            # Collect meaningful tags
            display_tags = []
            if tags.get("historic"):
                display_tags.append(tags["historic"].replace("_", " ").title())
            if tags.get("tourism"):
                display_tags.append(tags["tourism"].replace("_", " ").title())
            if tags.get("amenity"):
                display_tags.append(tags["amenity"].replace("_", " ").title())
            if tags.get("cuisine"):
                display_tags.append(tags["cuisine"].replace("_", " ").title())

            seen_names.add(norm_name)
            seen_ids.add(full_id)

            parsed_places.append({
                "id": full_id,
                "provider": "openstreetmap",
                "provider_id": f"{el_type}/{el_id}",
                "name": name_clean,
                "category": cat,
                "address": address,
                "lat": float(p_lat),
                "lon": float(p_lon),
                "osm_wikipedia": wiki_tag,
                "osm_wikidata": wikidata_tag,
                "osm_image": img_tag,
                "phone": tags.get("phone") or tags.get("contact:phone"),
                "website": tags.get("website") or tags.get("contact:website") or tags.get("url"),
                "opening_hours": tags.get("opening_hours"),
                "tags": display_tags[:4]
            })

        self._set_cache(cache_key, parsed_places)
        return parsed_places


# Singleton instance
overpass_service = OverpassService()
