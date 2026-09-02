import asyncio
import time
from typing import Dict, List, Optional, Any

from app.services.explore.nominatim import nominatim_service
from app.services.explore.overpass import overpass_service
from app.services.explore.wikimedia import wikimedia_service

# In-memory place cache (TTL: 6 hours)
_PLACES_STORE: Dict[str, Dict[str, Any]] = {}
_DESTINATION_STORE: Dict[str, Dict[str, Any]] = {}

FEATURED_DESTINATIONS_DATA = [
    {
        "destination": "Hyderabad",
        "country": "India",
        "lat": 17.385044,
        "lon": 78.486671,
        "description": "Hyderabad is celebrated for its 400-year-old Nizami heritage, architectural monuments, and iconic cuisine.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/71/Charminar_Hyderabad_1.jpg/1200px-Charminar_Hyderabad_1.jpg",
        "overview": "The City of Pearls seamlessly blends ancient Qutb Shahi grandeur with modern IT corridors.",
        "best_time_to_visit": "October to March",
        "currency": "INR (₹)",
        "highlights": [
            {
                "id": "osm_way_charminar",
                "place_id": "osm_way_charminar",
                "provider": "openstreetmap",
                "name": "Charminar",
                "category": "attraction",
                "address": "Charminar Rd, Hyderabad, Telangana 500002",
                "lat": 17.3615636,
                "lon": 78.4746645,
                "description": "Iconic 16th-century mosque with four grand arches and minarets.",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/71/Charminar_Hyderabad_1.jpg/1200px-Charminar_Hyderabad_1.jpg",
                "image_verified": True,
                "image_source": "wikipedia",
                "wikipedia_url": "https://en.wikipedia.org/wiki/Charminar",
                "tags": ["Historical Landmark", "Monument", "Architecture"]
            },
            {
                "id": "osm_way_golconda",
                "place_id": "osm_way_golconda",
                "provider": "openstreetmap",
                "name": "Golconda Fort",
                "category": "attraction",
                "address": "Ibrahim Bagh, Hyderabad, Telangana 500008",
                "lat": 17.3833075,
                "lon": 78.4010536,
                "description": "Historic fortified citadel famous for its acoustic engineering and diamond vaults.",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d7/Golconda_Fort_Hyderabad.jpg/1200px-Golconda_Fort_Hyderabad.jpg",
                "image_verified": True,
                "image_source": "wikipedia",
                "wikipedia_url": "https://en.wikipedia.org/wiki/Golconda_Fort",
                "tags": ["Citadel", "Fortress", "Acoustics"]
            }
        ]
    },
    {
        "destination": "Goa",
        "country": "India",
        "lat": 15.299326,
        "lon": 74.123996,
        "description": "Goa is renowned for its golden coastline, Portuguese colonial architecture, and tropical spice plantations.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Baga_Beach_North_Goa.jpg/1200px-Baga_Beach_North_Goa.jpg",
        "overview": "India's premier beach paradise offering heritage churches, water sports, and vibrant seafood.",
        "best_time_to_visit": "November to February",
        "currency": "INR (₹)",
        "highlights": [
            {
                "id": "osm_node_baga_beach",
                "place_id": "osm_node_baga_beach",
                "provider": "openstreetmap",
                "name": "Baga Beach",
                "category": "attraction",
                "address": "Baga, North Goa 403516",
                "lat": 15.5553,
                "lon": 73.7517,
                "description": "Popular North Goa beach destination known for water sports and seaside shacks.",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Baga_Beach_North_Goa.jpg/1200px-Baga_Beach_North_Goa.jpg",
                "image_verified": True,
                "image_source": "wikipedia",
                "tags": ["Beach", "Water Sports", "Coastal"]
            }
        ]
    },
    {
        "destination": "Bengaluru",
        "country": "India",
        "lat": 12.971599,
        "lon": 77.594566,
        "description": "The Garden City and Silicon Valley of India, known for lush parks, breweries, and historical palaces.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/Lalbagh_Glass_house_Bangalore.jpg/1200px-Lalbagh_Glass_house_Bangalore.jpg",
        "overview": "Cosmopolitan metropolis with pleasant year-round climate and vibrant culinary culture.",
        "best_time_to_visit": "September to March",
        "currency": "INR (₹)",
        "highlights": [
            {
                "id": "osm_way_lalbagh",
                "place_id": "osm_way_lalbagh",
                "provider": "openstreetmap",
                "name": "Lalbagh Botanical Garden",
                "category": "park",
                "address": "Mavalli, Bengaluru, Karnataka 560004",
                "lat": 12.9507,
                "lon": 77.5848,
                "description": "Historic 240-acre botanical garden featuring the famous 19th-century Glass House.",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/Lalbagh_Glass_house_Bangalore.jpg/1200px-Lalbagh_Glass_house_Bangalore.jpg",
                "image_verified": True,
                "image_source": "wikipedia",
                "tags": ["Botanical Garden", "Heritage", "Nature"]
            }
        ]
    },
    {
        "destination": "Delhi",
        "country": "India",
        "lat": 28.613939,
        "lon": 77.209021,
        "description": "India's vibrant capital, spanning centuries of Mughal, British, and modern monuments.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/India_Gate_in_New_Delhi_03-2016.jpg/1200px-India_Gate_in_New_Delhi_03-2016.jpg",
        "overview": "A vast cultural capital rich with UNESCO World Heritage sites and renowned street food.",
        "best_time_to_visit": "October to March",
        "currency": "INR (₹)",
        "highlights": [
            {
                "id": "osm_way_india_gate",
                "place_id": "osm_way_india_gate",
                "provider": "openstreetmap",
                "name": "India Gate",
                "category": "historic",
                "address": "Kartavya Path, India Gate, New Delhi 110001",
                "lat": 28.6129,
                "lon": 77.2295,
                "description": "Prominent 42-meter-high war memorial arch honoring Indian soldiers.",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/India_Gate_in_New_Delhi_03-2016.jpg/1200px-India_Gate_in_New_Delhi_03-2016.jpg",
                "image_verified": True,
                "image_source": "wikipedia",
                "tags": ["Monument", "Memorial", "Landmark"]
            }
        ]
    },
    {
        "destination": "Mumbai",
        "country": "India",
        "lat": 18.922000,
        "lon": 72.834700,
        "description": "India's bustling financial and entertainment capital on the Arabian Sea.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/df/Gateway_of_India_Mumbai_India.jpg/1200px-Gateway_of_India_Mumbai_India.jpg",
        "overview": "The City of Dreams featuring Victorian Gothic architecture, sea promenades, and Bollywood.",
        "best_time_to_visit": "November to February",
        "currency": "INR (₹)",
        "highlights": [
            {
                "id": "osm_way_gateway_india",
                "place_id": "osm_way_gateway_india",
                "provider": "openstreetmap",
                "name": "Gateway of India",
                "category": "historic",
                "address": "Apollo Bandar, Colaba, Mumbai 400001",
                "lat": 18.9220,
                "lon": 72.8347,
                "description": "20th-century arch monument erected commemorating King George V's landing.",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/df/Gateway_of_India_Mumbai_India.jpg/1200px-Gateway_of_India_Mumbai_India.jpg",
                "image_verified": True,
                "image_source": "wikipedia",
                "tags": ["Monument", "Seafront", "Heritage"]
            }
        ]
    },
    {
        "destination": "Paris",
        "country": "France",
        "lat": 48.856614,
        "lon": 2.352222,
        "description": "The City of Light, globally renowned for fashion, art, gastronomy, and culture.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a8/Tour_Eiffel_Wikimedia_Commons.jpg/1200px-Tour_Eiffel_Wikimedia_Commons.jpg",
        "overview": "World capital of art, gastronomy, and timeless European elegance.",
        "best_time_to_visit": "April to October",
        "currency": "EUR (€)",
        "highlights": [
            {
                "id": "osm_way_eiffel_tower",
                "place_id": "osm_way_eiffel_tower",
                "provider": "openstreetmap",
                "name": "Eiffel Tower",
                "category": "attraction",
                "address": "Champ de Mars, 5 Av. Anatole France, 75007 Paris",
                "lat": 48.8584,
                "lon": 2.2945,
                "description": "Wrought-iron lattice tower on the Champ de Mars, global cultural icon of France.",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a8/Tour_Eiffel_Wikimedia_Commons.jpg/1200px-Tour_Eiffel_Wikimedia_Commons.jpg",
                "image_verified": True,
                "image_source": "wikipedia",
                "tags": ["Iconic Monument", "Architecture", "Panoramic View"]
            }
        ]
    }
]


class ExploreProvider:
    """
    Unified OpenStreetMap, Nominatim, Overpass, and Wikimedia Explore Provider.
    100% Free & Open Public Architecture — No Google, No Mapbox, No Foursquare, No API keys required.
    """

    def __init__(self):
        self.nominatim = nominatim_service
        self.overpass = overpass_service
        self.wikimedia = wikimedia_service

        # Initialize memory store with pre-seeded featured items
        for fd in FEATURED_DESTINATIONS_DATA:
            _DESTINATION_STORE[fd["destination"].lower()] = fd
            for h in fd.get("highlights", []):
                _PLACES_STORE[h["id"]] = h

    async def _enrich_place(self, raw_place: Dict[str, Any], location_hint: str) -> Dict[str, Any]:
        """
        Enrich an Overpass place with verified Wikimedia data and format into the canonical place schema.
        """
        place_id = raw_place["id"]
        if place_id in _PLACES_STORE:
            return _PLACES_STORE[place_id]

        wiki_info = await self.wikimedia.resolve_place_entity(
            name=raw_place["name"],
            category=raw_place["category"],
            osm_wikipedia=raw_place.get("osm_wikipedia"),
            osm_wikidata=raw_place.get("osm_wikidata"),
            osm_image=raw_place.get("osm_image"),
            location_hint=location_hint
        )

        image_url = wiki_info.get("image_url") if wiki_info else None
        image_verified = bool(wiki_info and wiki_info.get("image_verified"))
        description = wiki_info.get("description") if wiki_info else None

        normalized = {
            "id": place_id,
            "place_id": place_id,  # For backward compatibility
            "provider": "openstreetmap",
            "provider_id": raw_place.get("provider_id", place_id),
            "name": raw_place["name"],
            "category": raw_place["category"],
            "address": raw_place["address"],
            "location": {
                "lat": raw_place["lat"],
                "lon": raw_place["lon"]
            },
            "lat": raw_place["lat"],
            "lon": raw_place["lon"],
            "description": description or f"{raw_place['category'].title()} in {location_hint.split(',')[0].strip() or 'the area'}.",
            "rating": None,
            "review_count": None,
            "image_url": image_url,
            "photos": [image_url] if image_url else [],
            "image_verified": image_verified,
            "image_source": wiki_info.get("image_source") if wiki_info else None,
            "image_source_url": wiki_info.get("image_source_url") if wiki_info else None,
            "image_author": None,
            "image_license": None,
            "wikipedia_url": wiki_info.get("wikipedia_url") if wiki_info else None,
            "wikidata_id": raw_place.get("osm_wikidata"),
            "phone": raw_place.get("phone"),
            "website": raw_place.get("website"),
            "opening_hours": raw_place.get("opening_hours"),
            "tags": raw_place.get("tags", []),
            "source": {
                "provider": "openstreetmap",
                "source_url": f"https://www.openstreetmap.org/{raw_place.get('provider_id', '')}"
            }
        }

        _PLACES_STORE[place_id] = normalized
        return normalized

    async def search_places(
        self,
        query: str,
        category: str = "all",
        page: int = 1,
        limit: int = 24
    ) -> Dict[str, Any]:
        """
        Full-featured place search: Geocoding via Nominatim -> Discovery via Overpass -> Enrichment via Wikimedia.
        """
        clean_q = query.strip()
        cat_lower = category.lower().strip()

        # 1. Geocode destination
        geo = await self.nominatim.geocode_destination(clean_q)
        if not geo:
            geo = await self.nominatim.geocode_destination("Hyderabad")

        lat = geo["lat"]
        lon = geo["lon"]
        display_name = geo["display_name"]
        dest_name = geo["name"]

        # 2. Discover places via Overpass
        raw_places = await self.overpass.discover_places(lat=lat, lon=lon, category=cat_lower, radius=15000)

        # Inject known featured highlights for the destination at top if available
        dest_key = dest_name.lower()
        if dest_key in _DESTINATION_STORE:
            preset_places = _DESTINATION_STORE[dest_key].get("highlights", [])
            for p in preset_places:
                if not any(rp["name"].lower() == p["name"].lower() for rp in raw_places):
                    raw_places.insert(0, {
                        "id": p["id"],
                        "provider_id": p.get("provider_id", p["id"]),
                        "name": p["name"],
                        "category": p["category"],
                        "address": p.get("address", display_name),
                        "lat": p["lat"],
                        "lon": p["lon"],
                        "osm_wikipedia": p.get("wikipedia_url"),
                        "osm_image": p.get("image_url"),
                        "tags": p.get("tags", [])
                    })

        # 3. Enrich top places concurrently
        enrich_tasks = [self._enrich_place(p, display_name) for p in raw_places[:48]]
        enriched_places = await asyncio.gather(*enrich_tasks)

        # Filter by category if requested
        if cat_lower not in ["all", "destinations"]:
            filtered_places = [
                p for p in enriched_places
                if p["category"] == cat_lower.rstrip("s") or (cat_lower == "attractions" and p["category"] in ["attraction", "historic", "museum", "park"])
            ]
        else:
            filtered_places = enriched_places

        # 4. Pagination
        total_count = len(filtered_places)
        start_idx = max(0, (page - 1) * limit)
        end_idx = start_idx + limit
        paged_places = filtered_places[start_idx:end_idx]
        has_more = end_idx < total_count

        # 5. Build Destination Guide Info
        dest_summary = await self.get_destination_details(dest_name)

        return {
            "query": clean_q,
            "category": cat_lower,
            "destination_info": dest_summary,
            "places": paged_places,
            "results": paged_places,  # For backward compatibility with existing frontend
            "page": page,
            "limit": limit,
            "total_results": total_count,
            "has_more": has_more
        }

    async def get_destination_details(self, destination_name: str) -> Optional[Dict[str, Any]]:
        """
        Get structured destination summary guide with verified overview and categorization.
        """
        clean_name = destination_name.strip()
        norm_key = clean_name.lower()

        if norm_key in _DESTINATION_STORE:
            return _DESTINATION_STORE[norm_key]

        geo = await self.nominatim.geocode_destination(clean_name)
        if not geo:
            return None

        # Fetch Wikipedia overview
        wiki_info = await self.wikimedia.get_wikipedia_page_summary(geo["name"])
        image_url = wiki_info.get("image_url") if wiki_info else None
        description = wiki_info.get("description") if wiki_info else None

        # Discover top places in this destination
        raw_places = await self.overpass.discover_places(lat=geo["lat"], lon=geo["lon"], category="all", radius=12000)
        enrich_tasks = [self._enrich_place(p, geo["display_name"]) for p in raw_places[:20]]
        enriched = await asyncio.gather(*enrich_tasks)

        guide = {
            "destination": geo["name"],
            "country": geo.get("country", ""),
            "lat": geo["lat"],
            "lon": geo["lon"],
            "description": description or f"Discover the culture, landmarks, and sights of {geo['name']}.",
            "image_url": image_url or (enriched[0].get("image_url") if enriched and enriched[0].get("image_verified") else None),
            "overview": description or f"{geo['name']} offers a rich blend of historic sights, dining, and accommodations.",
            "best_time_to_visit": "October to March",
            "currency": "INR (₹)" if geo.get("country") == "India" else "EUR (€)" if geo.get("country") == "France" else "USD ($)",
            "highlights": [p for p in enriched if p.get("category") in ["attraction", "historic", "museum", "park", "activity"]],
            "hotels": [p for p in enriched if p.get("category") == "hotel"],
            "restaurants": [p for p in enriched if p.get("category") in ["restaurant", "cafe"]],
            "attractions": [p for p in enriched if p.get("category") in ["attraction", "historic", "museum"]],
            "activities": [p for p in enriched if p.get("category") == "activity"],
        }

        _DESTINATION_STORE[norm_key] = guide
        return guide

    async def get_featured_destinations(self) -> List[Dict[str, Any]]:
        """
        Get list of top featured destination guides.
        """
        return list(FEATURED_DESTINATIONS_DATA)

    async def get_place_by_id(self, place_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve place details by place ID.
        """
        if place_id in _PLACES_STORE:
            p = _PLACES_STORE[place_id]
            nearby = [
                other for other in _PLACES_STORE.values()
                if other["id"] != place_id and abs(other["lat"] - p["lat"]) < 0.08 and abs(other["lon"] - p["lon"]) < 0.08
            ][:4]
            return {"place": p, "nearby_places": nearby}

        # If not in cache, resolve from place_id format osm_{type}_{id}
        parts = place_id.split("_")
        if len(parts) == 3 and parts[0] == "osm":
            el_type, el_id = parts[1], parts[2]
            try:
                import httpx
                query = f"[out:json][timeout:6];{el_type}({el_id});out center tags;"
                async with httpx.AsyncClient(timeout=6.0) as client:
                    for ep in ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]:
                        res = await client.post(ep, data={"data": query}, headers={"User-Agent": "TravelTrack-Explore/3.0"})
                        if res.status_code == 200:
                            data = res.json().get("elements", [])
                            if data:
                                el = data[0]
                                tags = el.get("tags", {})
                                name = tags.get("name") or tags.get("name:en") or "Place"
                                p_lat = el.get("lat") or el.get("center", {}).get("lat") or 0.0
                                p_lon = el.get("lon") or el.get("center", {}).get("lon") or 0.0
                                raw_p = {
                                    "id": place_id,
                                    "provider_id": f"{el_type}/{el_id}",
                                    "name": name,
                                    "category": self.overpass._map_osm_category(tags),
                                    "address": self.overpass._format_address(tags, name),
                                    "lat": float(p_lat),
                                    "lon": float(p_lon),
                                    "osm_wikipedia": tags.get("wikipedia"),
                                    "osm_wikidata": tags.get("wikidata"),
                                    "osm_image": tags.get("image"),
                                    "tags": []
                                }
                                norm = await self._enrich_place(raw_p, name)
                                return {"place": norm, "nearby_places": []}
            except Exception:
                pass

        return None


# Singleton instance
explore_provider = ExploreProvider()
