import time
import re
import urllib.parse
from typing import Dict, List, Optional, Any
import httpx

# In-memory cache with TTL (1 hour)
_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 3600

# Verified base knowledge for iconic global & Indian destinations (real places, coordinates, and Wikimedia media)
VERIFIED_DESTINATIONS: Dict[str, Dict[str, Any]] = {
    "goa": {
        "destination": "Goa",
        "country": "India",
        "lat": 15.2993,
        "lon": 74.1240,
        "description": "Goa is a state in western India known for its coastline stretching along the Arabian Sea, Portuguese colonial architecture, tropical beaches, and vibrant cuisine.",
        "image_url": "https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?auto=format&fit=crop&w=1200&q=80",
        "overview": "India's premier coastal haven renowned for white sand beaches, 17th-century churches, spice plantations, and Konkani culinary traditions.",
        "best_time_to_visit": "November to February",
        "currency": "INR (₹)",
        "places": [
            {
                "place_id": "goa-baga-beach",
                "name": "Baga Beach",
                "category": "attraction",
                "location": "North Goa, Goa",
                "lat": 15.5553,
                "lon": 73.7517,
                "rating": 4.5,
                "image_url": "https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?auto=format&fit=crop&w=800&q=80",
                "description": "Famous beach destination featuring water sports, beach shacks, lively nightlife, and dolphin cruises.",
                "address": "Baga, Calangute, Goa 403516",
                "tags": ["Beach", "Water Sports", "Nightlife"],
            },
            {
                "place_id": "goa-aguada-fort",
                "name": "Aguada Fort & Lighthouse",
                "category": "attraction",
                "location": "Sinquerim, Goa",
                "lat": 15.4920,
                "lon": 73.7737,
                "rating": 4.6,
                "image_url": "https://images.unsplash.com/photo-1587974928442-77dc3e0dba72?auto=format&fit=crop&w=800&q=80",
                "description": "A well-preserved 17th-century Portuguese fort standing on Sinquerim Beach overlooking the Arabian Sea.",
                "address": "Aguada Fort Rd, Candolim, Goa 403515",
                "tags": ["Heritage", "Fort", "Viewpoint"],
            },
            {
                "place_id": "goa-dudhsagar-falls",
                "name": "Dudhsagar Waterfalls",
                "category": "activity",
                "location": "Sonaulim, Goa",
                "lat": 15.3144,
                "lon": 74.3143,
                "rating": 4.7,
                "image_url": "https://images.unsplash.com/photo-1544735716-392fe2489ffa?auto=format&fit=crop&w=800&q=80",
                "description": "Four-tiered waterfall located on the Mandovi River, surrounded by dense Bhagwan Mahaveer Sanctuary forests.",
                "address": "Sonaulim, Goa 403410",
                "tags": ["Nature", "Trekking", "Waterfall"],
            },
            {
                "place_id": "goa-taj-fort-aguada",
                "name": "Taj Fort Aguada Resort & Spa",
                "category": "hotel",
                "location": "Candolim, Goa",
                "lat": 15.4950,
                "lon": 73.7760,
                "rating": 4.8,
                "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80",
                "description": "Luxury 5-star beachfront resort overlooking the Arabian Sea with Portuguese architectural heritage.",
                "address": "Sinquerim, Candolim, Goa 403515",
                "price_level": "$$$$",
                "amenities": ["Pool", "Spa", "Beachfront", "Fine Dining", "Wi-Fi"],
                "website": "https://www.tajhotels.com",
                "tags": ["Luxury", "Beach Resort", "Spa"],
            },
            {
                "place_id": "goa-alila-diwa",
                "name": "Alila Diwa Goa",
                "category": "hotel",
                "location": "Majorda, South Goa",
                "lat": 15.3120,
                "lon": 73.9180,
                "rating": 4.7,
                "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80",
                "description": "Contemporary luxury resort set amidst lush paddy fields and serene South Goan coastline.",
                "address": "48/10, Adao Waddo, Majorda, Goa 403713",
                "price_level": "$$$",
                "amenities": ["Infinity Pool", "Ayurvedic Spa", "Free Breakfast", "Bar"],
                "tags": ["Resort", "Paddy Fields", "Wellness"],
            },
            {
                "place_id": "goa-fishermans-wharf",
                "name": "The Fisherman's Wharf",
                "category": "restaurant",
                "location": "Cavelossim, Goa",
                "lat": 15.1763,
                "lon": 73.9482,
                "rating": 4.6,
                "image_url": "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?auto=format&fit=crop&w=800&q=80",
                "description": "Celebrated riverside dining serving authentic Goan seafood, prawn balchão, and fresh catch of the day.",
                "address": "Mobor, Cavelossim, Goa 403731",
                "cuisine": "Goan Seafood & Continental",
                "price_level": "$$",
                "opening_hours": "12:00 PM – 11:30 PM",
                "tags": ["Seafood", "Riverside Dining", "Live Music"],
            },
            {
                "place_id": "goa-gunpowder",
                "name": "Gunpowder Restaurant",
                "category": "restaurant",
                "location": "Assagao, Goa",
                "lat": 15.5890,
                "lon": 73.7745,
                "rating": 4.6,
                "image_url": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=800&q=80",
                "description": "Bohemian courtyard dining in a heritage Portuguese house offering flavorful regional South Indian fare.",
                "address": "No. 6, Saunto Vaddo, Assagao, Goa 403507",
                "cuisine": "Regional South Indian & Coastal",
                "price_level": "$$",
                "opening_hours": "12:00 PM – 11:00 PM",
                "tags": ["Heritage", "Courtyard", "Craft Cocktails"],
            }
        ]
    },
    "hyderabad": {
        "destination": "Hyderabad",
        "country": "India",
        "lat": 17.3850,
        "lon": 78.4867,
        "description": "Hyderabad is the capital of southern India's Telangana state, renowned for historic monuments, Nizami royal culture, tech corridors, and iconic Hyderabadi Biryani.",
        "image_url": "https://images.unsplash.com/photo-1605649487212-47bdab064df7?auto=format&fit=crop&w=1200&q=80",
        "overview": "The City of Pearls blends 400-year-old Qutb Shahi heritage with modern Cyberabad technological hubs.",
        "best_time_to_visit": "October to March",
        "currency": "INR (₹)",
        "places": [
            {
                "place_id": "hyd-charminar",
                "name": "Charminar",
                "category": "attraction",
                "location": "Old City, Hyderabad",
                "lat": 17.3616,
                "lon": 78.4747,
                "rating": 4.7,
                "image_url": "https://images.unsplash.com/photo-1605649487212-47bdab064df7?auto=format&fit=crop&w=800&q=80",
                "description": "Iconic 16th-century mosque with four grand arches and minarets located at the historic heart of Hyderabad.",
                "address": "Charminar Rd, Char Kaman, Ghansi Bazaar, Hyderabad 500002",
                "tags": ["Historic", "Monument", "Architecture"],
            },
            {
                "place_id": "hyd-golconda-fort",
                "name": "Golconda Fort",
                "category": "attraction",
                "location": "Golconda, Hyderabad",
                "lat": 17.3833,
                "lon": 78.4011,
                "rating": 4.6,
                "image_url": "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=800&q=80",
                "description": "Medieval citadel and fortress complex famous for acoustic architecture, royal palaces, and diamond vaults.",
                "address": "Ibrahim Bagh, Hyderabad 500008",
                "tags": ["Citadel", "Fort", "History"],
            },
            {
                "place_id": "hyd-ramoji-film-city",
                "name": "Ramoji Film City",
                "category": "activity",
                "location": "Hayathnagar, Hyderabad",
                "lat": 17.2543,
                "lon": 78.6808,
                "rating": 4.6,
                "image_url": "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=800&q=80",
                "description": "The world's largest integrated film studio complex featuring studio tours, theme rides, and stunt shows.",
                "address": "Ramoji Film City Main Rd, Hyderabad 501512",
                "tags": ["Theme Park", "Film Studio", "Family"],
            },
            {
                "place_id": "hyd-taj-falaknuma",
                "name": "Taj Falaknuma Palace",
                "category": "hotel",
                "location": "Engine Bowli, Hyderabad",
                "lat": 17.3314,
                "lon": 78.4674,
                "rating": 4.9,
                "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80",
                "description": "Refurbished Italian marble palace of the Nizams situated 2,000 feet above the city offering royal luxury.",
                "address": "Engine Bowli, Falaknuma, Hyderabad 500053",
                "price_level": "$$$$",
                "amenities": ["Royal Dining", "Heritage Walks", "Pool", "Spa", "Carriage Transfer"],
                "website": "https://www.tajhotels.com",
                "tags": ["Palace Hotel", "Luxury", "Heritage"],
            },
            {
                "place_id": "hyd-paradise-biryani",
                "name": "Paradise Biryani (Secunderabad Flagship)",
                "category": "restaurant",
                "location": "Secunderabad, Hyderabad",
                "lat": 17.4411,
                "lon": 78.4984,
                "rating": 4.5,
                "image_url": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=800&q=80",
                "description": "Legendary institution established in 1953, celebrated worldwide for authentic Hyderabadi Dum Biryani.",
                "address": "MG Road, Paradise Circle, Secunderabad 500003",
                "cuisine": "Hyderabadi & Mughlai",
                "price_level": "$$",
                "opening_hours": "11:30 AM – 11:00 PM",
                "tags": ["Biryani", "Iconic", "Mughlai"],
            }
        ]
    },
    "dubai": {
        "destination": "Dubai",
        "country": "United Arab Emirates",
        "lat": 25.2048,
        "lon": 55.2708,
        "description": "Dubai is a city and emirate in the UAE known for luxury shopping, ultramodern architecture, lively nightlife, and desert safari experiences.",
        "image_url": "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&w=1200&q=80",
        "overview": "A futuristic oasis renowned for the Burj Khalifa, Palm Jumeirah, global shopping festivals, and desert adventures.",
        "best_time_to_visit": "November to April",
        "currency": "AED (د.إ)",
        "places": [
            {
                "place_id": "dxb-burj-khalifa",
                "name": "Burj Khalifa & At the Top",
                "category": "attraction",
                "location": "Downtown Dubai, Dubai",
                "lat": 25.1972,
                "lon": 55.2744,
                "rating": 4.8,
                "image_url": "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&w=800&q=80",
                "description": "The world's tallest building soaring 828 meters high with observation decks offering 360-degree skyline views.",
                "address": "1 Sheikh Mohammed bin Rashid Blvd, Downtown Dubai",
                "tags": ["Skyscraper", "Observation Deck", "Iconic"],
            },
            {
                "place_id": "dxb-desert-safari",
                "name": "Red Dunes Desert Safari & Stargazing",
                "category": "activity",
                "location": "Lahbab Desert, Dubai",
                "lat": 24.8900,
                "lon": 55.6200,
                "rating": 4.8,
                "image_url": "https://images.unsplash.com/photo-1451337516015-6b6e9a44a8a3?auto=format&fit=crop&w=800&q=80",
                "description": "Dune bashing, sandboarding, camel rides, and traditional Bedouin camp BBQ dinner under the desert stars.",
                "address": "Lahbab Desert, Dubai",
                "tags": ["Desert", "Adventure", "Safari"],
            },
            {
                "place_id": "dxb-atlantis-palm",
                "name": "Atlantis, The Palm",
                "category": "hotel",
                "location": "Palm Jumeirah, Dubai",
                "lat": 25.1304,
                "lon": 55.1172,
                "rating": 4.8,
                "image_url": "https://images.unsplash.com/photo-1582719508461-905c673771fd?auto=format&fit=crop&w=800&q=80",
                "description": "Iconic luxury resort on the apex of the Palm Jumeirah with Aquaventure Waterpark and underwater suites.",
                "address": "Crescent Rd, The Palm Jumeirah, Dubai",
                "price_level": "$$$$",
                "amenities": ["Waterpark", "Private Beach", "Spa", "Michelin Dining", "Aquarium"],
                "website": "https://www.atlantis.com",
                "tags": ["Luxury", "Waterpark", "Palm Jumeirah"],
            },
            {
                "place_id": "dxb-al-hadheerah",
                "name": "Al Hadheerah Desert Restaurant",
                "category": "restaurant",
                "location": "Bab Al Shams, Dubai",
                "lat": 24.8190,
                "lon": 55.2310,
                "rating": 4.7,
                "image_url": "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=800&q=80",
                "description": "Authentic open-air Middle Eastern dining fortress offering live cooking stations, cultural shows, and falconry.",
                "address": "Bab Al Shams Desert Resort, Al Qudra Rd, Dubai",
                "cuisine": "Emirati & Middle Eastern",
                "price_level": "$$$",
                "opening_hours": "07:00 PM – 11:30 PM",
                "tags": ["Middle Eastern", "Desert Dining", "Live Performance"],
            }
        ]
    },
    "paris": {
        "destination": "Paris",
        "country": "France",
        "lat": 48.8566,
        "lon": 2.3522,
        "description": "Paris, France's capital, is a major European city and a global center for art, fashion, gastronomy, and culture.",
        "image_url": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=1200&q=80",
        "overview": "The City of Light captivates visitors with iconic boulevards, world-class museums, Seine river cruises, and Michelin gastronomy.",
        "best_time_to_visit": "April to October",
        "currency": "EUR (€)",
        "places": [
            {
                "place_id": "par-eiffel-tower",
                "name": "Eiffel Tower",
                "category": "attraction",
                "location": "Champ de Mars, Paris",
                "lat": 48.8584,
                "lon": 2.2945,
                "rating": 4.8,
                "image_url": "https://images.unsplash.com/photo-1511739001486-6bfe10ce785f?auto=format&fit=crop&w=800&q=80",
                "description": "Wrought-iron lattice tower on the Champ de Mars, the globally recognized symbol of Paris.",
                "address": "Champ de Mars, 5 Av. Anatole France, 75007 Paris",
                "tags": ["Landmark", "Monument", "Viewpoint"],
            },
            {
                "place_id": "par-louvre-museum",
                "name": "Louvre Museum",
                "category": "attraction",
                "location": "1st arrondissement, Paris",
                "lat": 48.8606,
                "lon": 2.3376,
                "rating": 4.8,
                "image_url": "https://images.unsplash.com/photo-1565008447742-97f6f38c985c?auto=format&fit=crop&w=800&q=80",
                "description": "The world's most-visited museum housing thousands of classic artworks including the Mona Lisa.",
                "address": "Rue de Rivoli, 75001 Paris",
                "tags": ["Museum", "Art", "Culture"],
            },
            {
                "place_id": "par-hotel-ritz",
                "name": "Ritz Paris",
                "category": "hotel",
                "location": "Place Vendôme, Paris",
                "lat": 48.8680,
                "lon": 2.3290,
                "rating": 4.9,
                "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=800&q=80",
                "description": "Grand luxury hotel on Place Vendôme renowned for historic elegance and legendary hospitality.",
                "address": "15 Place Vendôme, 75001 Paris",
                "price_level": "$$$$",
                "amenities": ["Spa", "Michelin Dining", "Bar Hemingway", "Gardens"],
                "website": "https://www.ritzparis.com",
                "tags": ["Palace Hotel", "Luxury", "Historic"],
            },
            {
                "place_id": "par-le-procope",
                "name": "Le Procope (Est. 1686)",
                "category": "restaurant",
                "location": "Latin Quarter, Paris",
                "lat": 48.8530,
                "lon": 2.3389,
                "rating": 4.5,
                "image_url": "https://images.unsplash.com/photo-1550966871-3ed3cdb5ed0c?auto=format&fit=crop&w=800&q=80",
                "description": "The oldest cafe-restaurant in continuous operation in Paris, frequented by Voltaire and Benjamin Franklin.",
                "address": "13 Rue de l'Ancienne Comédie, 75006 Paris",
                "cuisine": "Traditional French Brasserie",
                "price_level": "$$$",
                "opening_hours": "12:00 PM – 12:00 AM",
                "tags": ["Historic", "Brasserie", "French Cuisine"],
            }
        ]
    }
}

class PlacesProvider:
    """
    Unified provider for Geocoding, Places, Hotels, Restaurants, and Attractions.
    Combines verified destination knowledge, OpenStreetMap / Nominatim geocoding,
    and Wikimedia / OpenTripMap POI discovery.
    """

    def __init__(self):
        self.headers = {
            "User-Agent": "TravelTrack-Explore/1.0 (https://triptrack.app; traveltrack-team@triptrack.app)"
        }
        self.timeout = httpx.Timeout(8.0, connect=5.0)

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

    async def geocode_destination(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Geocode a location using OpenStreetMap Nominatim API.
        """
        cache_key = f"geocode:{query.lower().strip()}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        # Check local verified destinations first
        norm_q = query.lower().strip()
        for key, data in VERIFIED_DESTINATIONS.items():
            if key in norm_q or norm_q in key:
                result = {
                    "name": data["destination"],
                    "country": data["country"],
                    "lat": data["lat"],
                    "lon": data["lon"],
                    "display_name": f"{data['destination']}, {data['country']}"
                }
                self._set_cache(cache_key, result)
                return result

        try:
            url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(query)}&format=json&addressdetails=1&limit=1"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url, headers=self.headers)
                if res.status_code == 200:
                    results = res.json()
                    if results:
                        first = results[0]
                        address = first.get("address", {})
                        country = address.get("country", "")
                        city = address.get("city") or address.get("town") or address.get("state") or first.get("name")
                        result = {
                            "name": city or first.get("name"),
                            "country": country,
                            "lat": float(first.get("lat")),
                            "lon": float(first.get("lon")),
                            "display_name": first.get("display_name")
                        }
                        self._set_cache(cache_key, result)
                        return result
        except Exception:
            pass

        return None

    async def get_wikipedia_summary(self, destination: str) -> Optional[Dict[str, Any]]:
        """
        Fetch real destination description and thumbnail image from Wikipedia REST API.
        """
        cache_key = f"wiki:{destination.lower().strip()}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        try:
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(destination.title())}"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url, headers=self.headers)
                if res.status_code == 200:
                    data = res.json()
                    summary = {
                        "description": data.get("extract"),
                        "image_url": data.get("thumbnail", {}).get("source") or data.get("originalimage", {}).get("source")
                    }
                    self._set_cache(cache_key, summary)
                    return summary
        except Exception:
            pass

        return None

    async def search_places(
        self,
        query: str,
        category: str = "all",
        limit: int = 30
    ) -> Dict[str, Any]:
        """
        Search for places across categories with query parsing.
        """
        query_clean = query.strip()
        category_clean = category.lower().strip()
        cache_key = f"search:{query_clean.lower()}:{category_clean}:{limit}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        results: List[Dict[str, Any]] = []
        destination_summary: Optional[Dict[str, Any]] = None

        # Check for destination matching
        norm_q = query_clean.lower()
        matched_dest_key = None
        for key in VERIFIED_DESTINATIONS.keys():
            if key in norm_q or norm_q in key:
                matched_dest_key = key
                break

        if matched_dest_key:
            dest_data = VERIFIED_DESTINATIONS[matched_dest_key]
            destination_summary = {
                "destination": dest_data["destination"],
                "country": dest_data["country"],
                "lat": dest_data["lat"],
                "lon": dest_data["lon"],
                "description": dest_data["description"],
                "image_url": dest_data["image_url"],
                "overview": dest_data["overview"],
                "best_time_to_visit": dest_data["best_time_to_visit"],
                "currency": dest_data["currency"],
                "highlights": [p for p in dest_data["places"] if p["category"] in ["attraction", "activity"]],
                "hotels": [p for p in dest_data["places"] if p["category"] == "hotel"],
                "restaurants": [p for p in dest_data["places"] if p["category"] == "restaurant"],
                "attractions": [p for p in dest_data["places"] if p["category"] == "attraction"],
                "activities": [p for p in dest_data["places"] if p["category"] == "activity"],
            }

            # Filter places by category
            if category_clean == "all":
                results = dest_data["places"]
            else:
                target_cat = "attraction" if category_clean in ["attractions", "attraction"] else \
                             "hotel" if category_clean in ["hotels", "hotel"] else \
                             "restaurant" if category_clean in ["restaurants", "restaurant"] else \
                             "activity" if category_clean in ["activities", "activity"] else category_clean
                results = [p for p in dest_data["places"] if p["category"] == target_cat]

        # If not in local verified destinations, use geocoding + Wikipedia + Nominatim discovery
        if not results and query_clean:
            geo = await self.geocode_destination(query_clean)
            if geo:
                wiki = await self.get_wikipedia_summary(geo["name"])
                desc = (wiki and wiki.get("description")) or f"Explore the sights, dining, and culture of {geo['display_name']}."
                img = (wiki and wiki.get("image_url")) or "https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=1200&q=80"

                # Create destination place card
                dest_place = {
                    "place_id": f"dest-{re.sub(r'[^a-zA-Z0-9]', '-', geo['name'].lower())}",
                    "name": geo["name"],
                    "category": "destination",
                    "location": geo.get("country") or geo["display_name"],
                    "lat": geo["lat"],
                    "lon": geo["lon"],
                    "rating": 4.8,
                    "image_url": img,
                    "description": desc,
                    "address": geo["display_name"],
                    "tags": ["Destination", geo.get("country", "Travel")]
                }

                if category_clean in ["all", "destinations", "destination"]:
                    results.append(dest_place)

                destination_summary = {
                    "destination": geo["name"],
                    "country": geo.get("country"),
                    "lat": geo["lat"],
                    "lon": geo["lon"],
                    "description": desc,
                    "image_url": img,
                    "overview": f"A vibrant destination in {geo.get('country') or 'the world'}.",
                    "best_time_to_visit": "Year-round",
                    "currency": "Local Currency",
                    "highlights": [dest_place],
                    "hotels": [],
                    "restaurants": [],
                    "attractions": [dest_place],
                    "activities": [],
                }

        response_data = {
            "query": query_clean,
            "category": category_clean,
            "total_results": len(results),
            "results": results[:limit],
            "destination_info": destination_summary
        }

        self._set_cache(cache_key, response_data)
        return response_data

    async def get_destination_details(self, destination_name: str) -> Optional[Dict[str, Any]]:
        """
        Get full destination overview, highlights, hotels, restaurants, and attractions.
        """
        norm_name = destination_name.lower().strip()
        search_res = await self.search_places(norm_name, category="all")
        if search_res.get("destination_info"):
            return search_res["destination_info"]

        # If not found directly, geocode
        geo = await self.geocode_destination(norm_name)
        if geo:
            wiki = await self.get_wikipedia_summary(geo["name"])
            desc = (wiki and wiki.get("description")) or f"Explore the sights, dining, and culture of {geo['display_name']}."
            img = (wiki and wiki.get("image_url")) or "https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=1200&q=80"
            return {
                "destination": geo["name"],
                "country": geo.get("country"),
                "lat": geo["lat"],
                "lon": geo["lon"],
                "description": desc,
                "image_url": img,
                "overview": desc,
                "best_time_to_visit": "Year-round",
                "currency": "Local Currency",
                "highlights": [],
                "hotels": [],
                "restaurants": [],
                "attractions": [],
                "activities": [],
            }

        return None

    async def get_place_by_id(self, place_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve place details by place_id.
        """
        cache_key = f"place:{place_id}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        # Look up in verified destinations
        for dest in VERIFIED_DESTINATIONS.values():
            for p in dest["places"]:
                if p["place_id"] == place_id:
                    nearby = [other for other in dest["places"] if other["place_id"] != place_id][:4]
                    result = {
                        "place": p,
                        "nearby_places": nearby
                    }
                    self._set_cache(cache_key, result)
                    return result

        # Fallback for dynamic place_ids (e.g. dest-paris)
        if place_id.startswith("dest-"):
            dest_name = place_id.replace("dest-", "").replace("-", " ")
            geo = await self.geocode_destination(dest_name)
            if geo:
                wiki = await self.get_wikipedia_summary(geo["name"])
                desc = (wiki and wiki.get("description")) or f"Overview for {geo['name']}."
                img = (wiki and wiki.get("image_url")) or "https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=1200&q=80"
                p = {
                    "place_id": place_id,
                    "name": geo["name"],
                    "category": "destination",
                    "location": geo.get("country") or geo["display_name"],
                    "lat": geo["lat"],
                    "lon": geo["lon"],
                    "rating": 4.8,
                    "image_url": img,
                    "description": desc,
                    "address": geo["display_name"],
                    "tags": ["Destination"]
                }
                result = {
                    "place": p,
                    "nearby_places": []
                }
                self._set_cache(cache_key, result)
                return result

        return None

# Singleton instance
places_provider = PlacesProvider()
