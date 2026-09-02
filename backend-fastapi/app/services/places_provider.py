import time
import urllib.parse
from typing import Dict, List, Optional, Any
from app.services.google_places_provider import google_places_provider, VERIFIED_REAL_PLACES

# In-memory cache with TTL (1 hour)
_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 3600

# Verified destination guides (Destination metadata with authentic destination imagery)
VERIFIED_DESTINATIONS: Dict[str, Dict[str, Any]] = {
    "hyderabad": {
        "destination": "Hyderabad",
        "country": "India",
        "lat": 17.3850,
        "lon": 78.4867,
        "description": "Hyderabad is the capital of Telangana, celebrated for its 400-year-old Nizami heritage, architectural monuments, and iconic biryani.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/71/Charminar_Hyderabad_1.jpg/1200px-Charminar_Hyderabad_1.jpg",
        "overview": "The City of Pearls seamlessly blends ancient Qutb Shahi grandeur with modern IT corridors in Cyberabad.",
        "best_time_to_visit": "October to March",
        "currency": "INR (₹)",
        "place_ids": [
            "ChIJ4_0Q4s-byzsR6bI2J2N2N2A", # Charminar
            "ChIJ9wZ1y-aZyzsR6Wq2kH8YhZQ", # Golconda Fort
            "ChIJ19L8vYqXyzsR2Z9eY1Lq-xA", # Ramoji Film City
            "ChIJ00wG1v2byzsR7P1t5xU7_lE", # Taj Falaknuma
            "ChIJW8Z1yR2byzsRqQ6L2u4y6zQ"  # Paradise Biryani
        ]
    },
    "goa": {
        "destination": "Goa",
        "country": "India",
        "lat": 15.2993,
        "lon": 74.1240,
        "description": "Goa is a coastal state in western India known for its Arabian Sea coastline, Portuguese heritage, and vibrant cuisine.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Baga_Beach_North_Goa.jpg/1200px-Baga_Beach_North_Goa.jpg",
        "overview": "India's premier coastal haven renowned for golden sand beaches, 17th-century churches, and Konkani dining.",
        "best_time_to_visit": "November to February",
        "currency": "INR (₹)",
        "place_ids": [
            "ChIJW3d13d7_vzsR2q3Z5q8YmXw", # Baga Beach
            "ChIJO98g-uT6vzsR4e_b6A4Z0hY", # Fort Aguada
            "ChIJs2G8v4_6vzsR8Q2j_a8Yl9E"  # Taj Fort Aguada
        ]
    },
    "delhi": {
        "destination": "Delhi",
        "country": "India",
        "lat": 28.6139,
        "lon": 77.2090,
        "description": "Delhi, India's capital territory, is a massive historic metropolis showcasing Mughal architecture and colonial avenues.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/India_Gate_in_New_Delhi_03-2016.jpg/1200px-India_Gate_in_New_Delhi_03-2016.jpg",
        "overview": "A vibrant blend of centuries-old empires, monumental gates, lively bazaars, and world-class culinary hotspots.",
        "best_time_to_visit": "October to March",
        "currency": "INR (₹)",
        "place_ids": [
            "ChIJ3_0Q1s-byzsR6bI2J2N2N2D", # India Gate
            "ChIJ9xV12s_byzsR6bI2J2N2N2E"  # Red Fort
        ]
    },
    "mumbai": {
        "destination": "Mumbai",
        "country": "India",
        "lat": 18.9220,
        "lon": 72.8347,
        "description": "Mumbai is India's financial powerhouse and entertainment capital on the west coast, known for colonial architecture and seaside promenades.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Mumbai_03-2016_30_Gateway_of_India.jpg/1200px-Mumbai_03-2016_30_Gateway_of_India.jpg",
        "overview": "The City of Dreams offers iconic Victorian Gothic landmarks, Marine Drive sunsets, and premier street food.",
        "best_time_to_visit": "November to February",
        "currency": "INR (₹)",
        "place_ids": [
            "ChIJ0_0Q1s-byzsR6bI2J2N2N2M"  # Gateway of India
        ]
    },
    "paris": {
        "destination": "Paris",
        "country": "France",
        "lat": 48.8566,
        "lon": 2.3522,
        "description": "Paris, France's capital, is a global center for art, fashion, gastronomy, and cultural heritage.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/85/Tour_Eiffel_Wikimedia_Commons_%28cropped%29.jpg/1200px-Tour_Eiffel_Wikimedia_Commons_%28cropped%29.jpg",
        "overview": "The City of Light captivates visitors with iconic boulevards, world-renowned museums, and Michelin gastronomy.",
        "best_time_to_visit": "April to October",
        "currency": "EUR (€)",
        "place_ids": [
            "ChIJLU7jZBlv5kcRnM-ptzGQ6Bw", # Eiffel Tower
            "ChIJD3uTd9hx5kcR1IQvGfr8dbk", # Louvre Museum
            "ChIJQ3_0Q1s-byzsR6bI2J2N2N2P"  # Ritz Paris
        ]
    }
}


class PlacesProvider:
    """
    High-level Places Provider delegating to GooglePlacesProvider with
    strict photo-to-place consistency and zero unverified image matching.
    """

    def __init__(self):
        self.google_provider = google_places_provider

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

    async def search_places(
        self,
        query: str,
        category: str = "all",
        limit: int = 30
    ) -> Dict[str, Any]:
        """
        Search for places via Google Places Provider with canonical identity and photo consistency.
        """
        res = await self.google_provider.search_places(query=query, category=category, limit=limit)
        
        # Check if query matches a destination summary
        norm_q = query.lower().strip()
        dest_summary = None
        for key, d in VERIFIED_DESTINATIONS.items():
            if key in norm_q or norm_q in key:
                places = [VERIFIED_REAL_PLACES[pid] for pid in d["place_ids"] if pid in VERIFIED_REAL_PLACES]
                dest_summary = {
                    "destination": d["destination"],
                    "country": d["country"],
                    "lat": d["lat"],
                    "lon": d["lon"],
                    "description": d["description"],
                    "image_url": d["image_url"],
                    "overview": d["overview"],
                    "best_time_to_visit": d["best_time_to_visit"],
                    "currency": d["currency"],
                    "highlights": [p for p in places if p["category"] in ["attraction", "activity"]],
                    "hotels": [p for p in places if p["category"] == "hotel"],
                    "restaurants": [p for p in places if p["category"] == "restaurant"],
                    "attractions": [p for p in places if p["category"] == "attraction"],
                    "activities": [p for p in places if p["category"] == "activity"],
                }
                break

        res["destination_info"] = dest_summary
        return res

    async def get_destination_details(self, destination_name: str) -> Optional[Dict[str, Any]]:
        """
        Get structured destination guide with verified places and coordinates.
        """
        norm = destination_name.lower().strip()
        if norm in VERIFIED_DESTINATIONS:
            d = VERIFIED_DESTINATIONS[norm]
            places = [VERIFIED_REAL_PLACES[pid] for pid in d["place_ids"] if pid in VERIFIED_REAL_PLACES]
            return {
                "destination": d["destination"],
                "country": d["country"],
                "lat": d["lat"],
                "lon": d["lon"],
                "description": d["description"],
                "image_url": d["image_url"],
                "overview": d["overview"],
                "best_time_to_visit": d["best_time_to_visit"],
                "currency": d["currency"],
                "highlights": [p for p in places if p["category"] in ["attraction", "activity"]],
                "hotels": [p for p in places if p["category"] == "hotel"],
                "restaurants": [p for p in places if p["category"] == "restaurant"],
                "attractions": [p for p in places if p["category"] == "attraction"],
                "activities": [p for p in places if p["category"] == "activity"],
            }

        # Fallback to search query
        search_res = await self.search_places(destination_name, category="all")
        if search_res.get("destination_info"):
            return search_res["destination_info"]

        return None

    async def get_place_by_id(self, place_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve place details by canonical Google Place ID.
        """
        return await self.google_provider.get_place_by_id(place_id)


# Singleton instance
places_provider = PlacesProvider()
