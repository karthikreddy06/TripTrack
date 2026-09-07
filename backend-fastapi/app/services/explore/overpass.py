import asyncio
import re
import time
from typing import Dict, List, Optional, Any, Set
import httpx

# Public Overpass API mirrors ordered by speed and reliability
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://z.overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

# Canonical category mapping from OSM tags
OSM_CATEGORY_MAP = {
    # Attractions & Landmarks
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
    "city_gate": "historic",
    "tower": "historic",
    "tomb": "historic",
    "artwork": "attraction",
    "theme_park": "activity",
    "zoo": "activity",
    "aquarium": "activity",
    "water_park": "activity",
    "beach": "attraction",
    "waterfall": "attraction",
    "cliff": "attraction",
    # Museums & Culture
    "museum": "museum",
    "gallery": "museum",
    "planetarium": "activity",
    "theatre": "activity",
    "arts_centre": "activity",
    # Stays / Accommodations
    "hotel": "hotel",
    "hostel": "hotel",
    "guest_house": "hotel",
    "motel": "hotel",
    "resort": "hotel",
    "bed_and_breakfast": "hotel",
    # Dining / Food
    "restaurant": "restaurant",
    "food_court": "restaurant",
    "pub": "restaurant",
    "bar": "restaurant",
    "bistro": "restaurant",
    # Cafes
    "cafe": "cafe",
    "bakery": "cafe",
    "ice_cream": "cafe",
    # Parks / Nature
    "park": "park",
    "garden": "park",
    "nature_reserve": "park",
}

# Strict negative filter: Non-tourist amenities that MUST be discarded
EXCLUDED_AMENITIES: Set[str] = {
    "school", "college", "university", "kindergarten", "tuition", "language_school", "music_school",
    "driving_school", "training", "clinic", "hospital", "doctors", "dentist", "pharmacy",
    "veterinary", "bank", "atm", "bureau_de_change", "post_office", "police", "courthouse",
    "townhall", "government", "local_government", "social_facility", "fire_station",
    "waste_disposal", "car_wash", "car_repair", "fuel", "charging_station", "parking",
    "parking_space", "parking_entrance", "toilets", "bench", "drinking_water", "telephone",
    "recycling", "vending_machine", "place_of_worship_office", "political_office", "mortuary",
    "crematorium", "grave_yard", "childcare", "nursing_home", "veterinary_clinic", "storage",
    "car_rental", "compressed_air", "grit_bin", "parcel_locker", "public_bookcase"
}

# Strict negative filter: Commercial / administrative offices that MUST be discarded
EXCLUDED_OFFICES: Set[str] = {
    "government", "political_party", "educational_institution", "company", "lawyer",
    "estate_agent", "it", "ngo", "administrative", "employment_agency", "diplomatic",
    "telecommunication", "insurance", "financial", "consulting", "logistics", "accountant",
    "architect", "association", "cooperative", "courier", "tax_advisor", "travel_agent",
    "security", "advertising_agency", "quango", "foundation", "union"
}

# Non-tourist shops to discard unless explicitly searching shopping
EXCLUDED_SHOPS: Set[str] = {
    "convenience", "supermarket", "car", "car_repair", "car_parts", "tyres", "motorcycle",
    "hardware", "doityourself", "chemist", "optician", "medical_supply", "laundry",
    "dry_cleaning", "tailor", "hairdresser", "beauty", "massage", "tattoo", "butcher",
    "seafood", "greengrocer", "stationery", "copyshop", "printing",
    "electronics_repair", "mobile_phone", "pawnbroker", "funeral_directors", "storage",
    "glaziery", "trade", "wholesale", "dry_cleaners", "kiosk", "newsagent"
}

# Regex for common non-tourist establishments
EXCLUDED_NAME_REGEX = re.compile(
    r"\b(typewriting|shorthand|coaching|tuition|classes\b|institute of|academy of|"
    r"mla office|mp office|party office|political party|advocate|notary|attorney|law chambers|chambers\b|chembers\b|"
    r"xerox|photostat|dry cleaners|dental clinic|polyclinic|nursing home|pathology|"
    r"diagnostic|atm\b|branch\b|head office|sub office|consultancy|enterprises|"
    r"traders|services pvt|logistics|car wash|auto repair|tyre center|hardware store|"
    r"petrol pump|gas station|police station|chowki|post office|courier services|"
    r"warehouse|residential building|society office|cable network|broadband|trust\b|"
    r"academy\b|classes\b|residence\b|bungalow\b|house\b|apartments?\b)\b",
    re.IGNORECASE
)


class OverpassService:
    """
    Service for querying OpenStreetMap elements via the Overpass API.
    Provides 100% dynamic worldwide place discovery with strict noise exclusion.
    """

    def __init__(self):
        self.headers = {
            "User-Agent": "TravelTrack-App/5.0 (https://triptrack-frontend.onrender.com; contact: info@triptrack.app)",
            "Accept": "application/json",
        }
        self.timeout = httpx.Timeout(3.5, connect=1.2)
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

    def is_valid_travel_place(self, tags: Dict[str, str], name: str, category: str = "all") -> bool:
        """
        Strictly evaluate whether an OSM entity is a genuine travel/tourist place.
        Discards schools, offices, clinics, repair shops, typewriting institutes, private residences, etc.
        """
        if not name or len(name.strip()) < 2:
            return False

        name_clean = name.strip()

        # 1. Regex check for noise names
        if EXCLUDED_NAME_REGEX.search(name_clean):
            return False

        # 2. Check amenity blacklist
        amenity = tags.get("amenity", "").lower()
        if amenity in EXCLUDED_AMENITIES:
            return False

        # 3. Check office blacklist
        office = tags.get("office", "").lower()
        if office in EXCLUDED_OFFICES or (office and "office" in tags):
            return False

        # 4. Check craft blacklist
        if "craft" in tags:
            return False

        # 5. Check shop blacklist
        shop = tags.get("shop", "").lower()
        if shop in EXCLUDED_SHOPS:
            return False

        # 6. Check building blacklist
        building = tags.get("building", "").lower()
        if building in ["apartments", "residential", "office", "commercial", "industrial", "warehouse", "dormitory", "garage", "house"]:
            if "tourism" not in tags and "historic" not in tags:
                return False

        # Category-specific validity
        cat_lower = category.lower().strip()
        if cat_lower in ["attractions", "historic", "museums", "parks", "activities", "all"]:
            if amenity in ["fast_food", "fuel", "car_wash"]:
                return False

        return True

    def _map_osm_category(self, tags: Dict[str, str]) -> str:
        """
        Determine the canonical TravelTrack category from OSM tags.
        """
        if "historic" in tags and tags["historic"] in OSM_CATEGORY_MAP:
            return OSM_CATEGORY_MAP[tags["historic"]]
        if "tourism" in tags and tags["tourism"] in OSM_CATEGORY_MAP:
            return OSM_CATEGORY_MAP[tags["tourism"]]
        if "amenity" in tags and tags["amenity"] in OSM_CATEGORY_MAP:
            return OSM_CATEGORY_MAP[tags["amenity"]]
        if "leisure" in tags and tags["leisure"] in OSM_CATEGORY_MAP:
            return OSM_CATEGORY_MAP[tags["leisure"]]
        if "natural" in tags and tags["natural"] in OSM_CATEGORY_MAP:
            return OSM_CATEGORY_MAP[tags["natural"]]
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
        Construct an optimized Overpass QL query string for genuine travel places.
        Strictly queries tourism, historic, landmark, museum, and curated dining/stay entities.
        """
        cat_lower = category.lower().strip()

        if cat_lower in ["hotels", "stays"]:
            body = f"""
  node["tourism"~"hotel|resort|guest_house|hostel|motel"](around:{radius},{lat},{lon});
  way["tourism"~"hotel|resort|guest_house|hostel|motel"](around:{radius},{lat},{lon});
"""
        elif cat_lower in ["restaurants", "dining"]:
            body = f"""
  node["amenity"~"restaurant|food_court|bistro|pub"](around:{radius},{lat},{lon});
  way["amenity"~"restaurant|food_court|bistro|pub"](around:{radius},{lat},{lon});
"""
        elif cat_lower == "cafes":
            body = f"""
  node["amenity"="cafe"](around:{radius},{lat},{lon});
  node["shop"~"bakery|coffee|tea|pastry"](around:{radius},{lat},{lon});
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
  node["natural"~"beach|waterfall|cliff"](around:{radius},{lat},{lon});
"""
        elif cat_lower == "historic":
            body = f"""
  node["historic"~"monument|memorial|castle|fort|ruins|palace|archaeological_site|heritage|city_gate|tower|tomb"](around:{radius},{lat},{lon});
  way["historic"~"monument|memorial|castle|fort|ruins|palace|archaeological_site|heritage|city_gate|tower|tomb"](around:{radius},{lat},{lon});
"""
        elif cat_lower == "activities":
            body = f"""
  node["tourism"~"theme_park|zoo|aquarium|water_park"](around:{radius},{lat},{lon});
  way["tourism"~"theme_park|zoo|aquarium|water_park"](around:{radius},{lat},{lon});
  node["amenity"~"planetarium|theatre|arts_centre"](around:{radius},{lat},{lon});
"""
        elif cat_lower == "attractions":
            body = f"""
  node["tourism"~"attraction|museum|gallery|theme_park|zoo|aquarium|viewpoint"](around:{radius},{lat},{lon});
  way["tourism"~"attraction|museum|gallery|theme_park|zoo|aquarium|viewpoint"](around:{radius},{lat},{lon});
  node["historic"~"monument|memorial|castle|fort|ruins|palace|archaeological_site|heritage|city_gate|tower|tomb"](around:{radius},{lat},{lon});
  way["historic"~"monument|memorial|castle|fort|ruins|palace|archaeological_site|heritage|city_gate|tower|tomb"](around:{radius},{lat},{lon});
  node["natural"~"beach|waterfall|cliff|peak"](around:{radius},{lat},{lon});
  node["leisure"~"park|garden|nature_reserve"](around:{radius},{lat},{lon});
  way["leisure"~"park|garden|nature_reserve"](around:{radius},{lat},{lon});
"""
        else:  # "all"
            body = f"""
  node["tourism"~"attraction|museum|gallery|viewpoint|theme_park|zoo"](around:{radius},{lat},{lon});
  way["tourism"~"attraction|museum|gallery|viewpoint|theme_park|zoo"](around:{radius},{lat},{lon});
  node["historic"~"monument|memorial|castle|fort|palace|ruins|heritage|city_gate|tomb"](around:{radius},{lat},{lon});
  way["historic"~"monument|memorial|castle|fort|palace|ruins|heritage|archaeological_site|city_gate|tomb"](around:{radius},{lat},{lon});
  node["leisure"~"park|garden|nature_reserve"](around:{radius},{lat},{lon});
  way["leisure"~"park|garden|nature_reserve"](around:{radius},{lat},{lon});
  node["natural"~"beach|waterfall|cliff|peak"](around:{radius},{lat},{lon});
"""

        query = f"""[out:json][timeout:8];
(
{body}
);
out center tags 40;
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
        Query Overpass API around given coordinates and return deduplicated, normalized, noise-filtered place items.
        """
        cache_key = f"overpass:v6:{round(lat, 3)}:{round(lon, 3)}:{category.lower()}"
        cached = self._get_cache(cache_key)
        if cached is not None and len(cached) > 0:
            return cached

        query = self._build_overpass_query(lat, lon, category, radius)
        elements = []

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for ep in OVERPASS_ENDPOINTS[:3]:
                try:
                    res_elements = await self._query_single_endpoint(client, ep, query)
                    if res_elements:
                        elements = res_elements
                        break
                except Exception:
                    continue

        parsed_places: List[Dict[str, Any]] = []
        seen_names = set()
        seen_ids = set()

        for el in elements:
            tags = el.get("tags", {})
            name = tags.get("name:en") or tags.get("name") or tags.get("int_name")
            if not name:
                continue

            name_clean = name.strip()

            # Strict noise & blacklist filtering
            if not self.is_valid_travel_place(tags, name_clean, category):
                continue

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
                "tags": tags_list[:4],
                "raw_tags": tags
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
                            "tags": [],
                            "raw_tags": tags
                        }
                        self._set_cache(cache_key, [res])
                        return res
                except Exception:
                    continue

        return None


# Singleton instance
overpass_service = OverpassService()
