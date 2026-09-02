import time
import urllib.parse
from typing import Dict, Optional, Any
import httpx

# In-memory cache for geocoded destinations (TTL: 24 hours)
_GEO_CACHE: Dict[str, Dict[str, Any]] = {}
GEO_CACHE_TTL = 86400

# Reliable default coordinates for major destinations
KNOWN_DESTINATIONS: Dict[str, Dict[str, Any]] = {
    "hyderabad": {
        "name": "Hyderabad",
        "display_name": "Hyderabad, Telangana, India",
        "lat": 17.385044,
        "lon": 78.486671,
        "country": "India",
        "boundingbox": [17.2, 17.6, 78.2, 78.7]
    },
    "goa": {
        "name": "Goa",
        "display_name": "Goa, India",
        "lat": 15.299326,
        "lon": 74.123996,
        "country": "India",
        "boundingbox": [14.8, 15.8, 73.6, 74.4]
    },
    "bengaluru": {
        "name": "Bengaluru",
        "display_name": "Bengaluru, Karnataka, India",
        "lat": 12.971599,
        "lon": 77.594566,
        "country": "India",
        "boundingbox": [12.8, 13.2, 77.4, 77.8]
    },
    "mumbai": {
        "name": "Mumbai",
        "display_name": "Mumbai, Maharashtra, India",
        "lat": 18.922000,
        "lon": 72.834700,
        "country": "India",
        "boundingbox": [18.8, 19.3, 72.7, 73.0]
    },
    "delhi": {
        "name": "Delhi",
        "display_name": "Delhi, India",
        "lat": 28.613939,
        "lon": 77.209021,
        "country": "India",
        "boundingbox": [28.4, 28.9, 76.8, 77.4]
    },
    "chennai": {
        "name": "Chennai",
        "display_name": "Chennai, Tamil Nadu, India",
        "lat": 13.082680,
        "lon": 80.270718,
        "country": "India",
        "boundingbox": [12.9, 13.3, 80.1, 80.4]
    },
    "jaipur": {
        "name": "Jaipur",
        "display_name": "Jaipur, Rajasthan, India",
        "lat": 26.912434,
        "lon": 75.787271,
        "country": "India",
        "boundingbox": [26.7, 27.1, 75.6, 76.0]
    },
    "tirupati": {
        "name": "Tirupati",
        "display_name": "Tirupati, Andhra Pradesh, India",
        "lat": 13.628756,
        "lon": 79.419179,
        "country": "India",
        "boundingbox": [13.5, 13.8, 79.2, 79.6]
    },
    "paris": {
        "name": "Paris",
        "display_name": "Paris, Île-de-France, France",
        "lat": 48.856614,
        "lon": 2.352222,
        "country": "France",
        "boundingbox": [48.7, 49.0, 2.2, 2.5]
    },
    "london": {
        "name": "London",
        "display_name": "London, Greater London, England, United Kingdom",
        "lat": 51.507351,
        "lon": -0.127758,
        "country": "United Kingdom",
        "boundingbox": [51.3, 51.7, -0.5, 0.3]
    },
    "tokyo": {
        "name": "Tokyo",
        "display_name": "Tokyo, Japan",
        "lat": 35.676192,
        "lon": 139.650311,
        "country": "Japan",
        "boundingbox": [35.5, 35.9, 139.4, 140.0]
    },
    "dubai": {
        "name": "Dubai",
        "display_name": "Dubai, United Arab Emirates",
        "lat": 25.204849,
        "lon": 55.270783,
        "country": "United Arab Emirates",
        "boundingbox": [24.9, 25.4, 55.0, 55.6]
    },
    "singapore": {
        "name": "Singapore",
        "display_name": "Singapore",
        "lat": 1.352083,
        "lon": 103.819836,
        "country": "Singapore",
        "boundingbox": [1.1, 1.5, 103.6, 104.1]
    },
    "new york": {
        "name": "New York",
        "display_name": "New York, United States",
        "lat": 40.712776,
        "lon": -74.005974,
        "country": "United States",
        "boundingbox": [40.4, 40.9, -74.3, -73.7]
    }
}


class NominatimService:
    """
    OpenStreetMap Nominatim Geocoding Service.
    Resolves arbitrary city/destination search queries to exact geographic coordinates and bounding box.
    """

    def __init__(self):
        self.timeout = httpx.Timeout(6.0, connect=3.0)
        self.headers = {
            "User-Agent": "TravelTrack-Explore/3.0 (https://triptrack-frontend.onrender.com; contact: info@triptrack.app)"
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

    async def geocode_destination(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Geocode a destination or city query to normalized location metadata.
        """
        if not query or not query.strip():
            return None

        clean_q = query.strip()
        norm_key = clean_q.lower()

        # Check Cache
        cached = self._get_cache(norm_key)
        if cached is not None:
            return cached

        # Check curated known destinations first for instant fast response
        if norm_key in KNOWN_DESTINATIONS:
            data = KNOWN_DESTINATIONS[norm_key]
            self._set_cache(norm_key, data)
            return data

        for k, v in KNOWN_DESTINATIONS.items():
            if k == norm_key or norm_key.startswith(k + " ") or norm_key.endswith(" " + k):
                self._set_cache(norm_key, v)
                return v

        # Live Nominatim Search
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": clean_q,
            "format": "json",
            "addressdetails": 1,
            "extratags": 1,
            "limit": 3
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url, params=params, headers=self.headers)
                if res.status_code == 200:
                    data = res.json()
                    if isinstance(data, list) and len(data) > 0:
                        top = data[0]
                        display_name = top.get("display_name", clean_q)
                        name = top.get("name") or display_name.split(",")[0].strip()
                        address = top.get("address", {})
                        country = address.get("country", "")
                        lat = float(top.get("lat"))
                        lon = float(top.get("lon"))
                        bbox = [float(b) for b in top.get("boundingbox", [lat - 0.1, lat + 0.1, lon - 0.1, lon + 0.1])]

                        result = {
                            "name": name,
                            "display_name": display_name,
                            "lat": lat,
                            "lon": lon,
                            "country": country,
                            "boundingbox": bbox,
                            "type": top.get("type", "city"),
                            "importance": top.get("importance", 0.5)
                        }
                        self._set_cache(norm_key, result)
                        return result
        except Exception:
            pass

        return None


# Singleton instance
nominatim_service = NominatimService()
