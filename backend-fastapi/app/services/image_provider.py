import os
import time
import urllib.parse
from typing import Dict, List, Optional, Any
import httpx

# In-memory image cache with TTL (4 hours)
_IMAGE_CACHE: Dict[str, Dict[str, Any]] = {}
IMAGE_CACHE_TTL = 14400  # 4 hours


class ImageProvider:
    """
    Unified Image Provider implementing the strict priority:
    1. Google Place Photo (if verified Google Places photo reference available)
    2. Wikipedia / Wikimedia official landmark article photo
    3. Foursquare Place Photo (for hotels, restaurants, businesses if API key configured)
    4. None (clean botanical placeholder fallback)
    """

    def __init__(self):
        self.timeout = httpx.Timeout(5.0, connect=3.0)
        self.headers = {
            "User-Agent": "TravelTrack-Discovery/2.0 (https://triptrack-frontend.onrender.com; contact: info@triptrack.app)"
        }

    def _get_cache(self, key: str) -> Optional[Dict[str, Any]]:
        cached = _IMAGE_CACHE.get(key)
        if cached and (time.time() - cached["timestamp"]) < IMAGE_CACHE_TTL:
            return cached["data"]
        return None

    def _set_cache(self, key: str, data: Optional[Dict[str, Any]]):
        _IMAGE_CACHE[key] = {
            "timestamp": time.time(),
            "data": data
        }

    async def resolve_wikipedia_image(self, place_name: str, location_hint: str = "") -> Optional[Dict[str, Any]]:
        """
        Resolve landmark/attraction to its canonical Wikipedia article and extract its official lead photo.
        """
        if not place_name:
            return None

        clean_name = place_name.strip()
        cache_key = f"wiki_img:{clean_name.lower()}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        # Strategy A: Direct Wikipedia Page Summary
        # E.g. "Charminar", "Golconda_Fort", "Ramoji_Film_City", "Gateway_of_India"
        variants = [
            clean_name.replace(" ", "_"),
            f"{clean_name.replace(' ', '_')}_{location_hint.split(',')[0].strip()}".strip("_"),
        ]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for title in variants:
                try:
                    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
                    res = await client.get(url, headers=self.headers)
                    if res.status_code == 200:
                        data = res.json()
                        page_type = data.get("type", "")
                        if page_type not in ["disambiguation", "no-extract"]:
                            # Extract photo
                            original_img = data.get("originalimage", {}).get("source")
                            thumb_img = data.get("thumbnail", {}).get("source")
                            chosen_img = original_img or thumb_img

                            # Avoid tiny icon svgs or maps as lead photos if possible
                            if chosen_img and not chosen_img.endswith(".svg"):
                                result = {
                                    "image_url": chosen_img,
                                    "thumbnail_url": thumb_img or chosen_img,
                                    "source": "wikipedia",
                                    "source_page": data.get("content_urls", {}).get("desktop", {}).get("page"),
                                    "description": data.get("description") or data.get("extract"),
                                    "verified": True
                                }
                                self._set_cache(cache_key, result)
                                return result
                except Exception:
                    pass

            # Strategy B: Search Wikipedia OpenSearch API if direct title was not exact
            try:
                search_query = f"{clean_name} {location_hint}".strip()
                search_url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={urllib.parse.quote(search_query)}&limit=3&namespace=0&format=json"
                sres = await client.get(search_url, headers=self.headers)
                if sres.status_code == 200:
                    sdata = sres.json()
                    if len(sdata) >= 2 and sdata[1]:
                        top_title = sdata[1][0]
                        summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(top_title.replace(' ', '_'))}"
                        sum_res = await client.get(summary_url, headers=self.headers)
                        if sum_res.status_code == 200:
                            data = sum_res.json()
                            original_img = data.get("originalimage", {}).get("source")
                            thumb_img = data.get("thumbnail", {}).get("source")
                            chosen_img = original_img or thumb_img
                            if chosen_img and not chosen_img.endswith(".svg"):
                                result = {
                                    "image_url": chosen_img,
                                    "thumbnail_url": thumb_img or chosen_img,
                                    "source": "wikipedia",
                                    "source_page": data.get("content_urls", {}).get("desktop", {}).get("page"),
                                    "description": data.get("description") or data.get("extract"),
                                    "verified": True
                                }
                                self._set_cache(cache_key, result)
                                return result
            except Exception:
                pass

        self._set_cache(cache_key, None)
        return None

    async def resolve_foursquare_image(self, place_name: str, lat: Optional[float] = None, lon: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Resolve business/hotel/restaurant to Foursquare Places photo if API key configured.
        """
        fsq_key = os.getenv("FOURSQUARE_API_KEY", "").strip()
        if not fsq_key or not place_name:
            return None

        cache_key = f"fsq_img:{place_name.lower()}:{lat}:{lon}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        try:
            url = "https://api.foursquare.com/v3/places/search"
            headers = {
                "Accept": "application/json",
                "Authorization": fsq_key
            }
            params = {
                "query": place_name,
                "limit": 1,
                "fields": "fsq_id,name,photos"
            }
            if lat and lon:
                params["ll"] = f"{lat},{lon}"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url, headers=headers, params=params)
                if res.status_code == 200:
                    data = res.json()
                    results = data.get("results", [])
                    if results and results[0].get("photos"):
                        photos = results[0]["photos"]
                        if photos:
                            p = photos[0]
                            photo_url = f"{p.get('prefix')}original{p.get('suffix')}"
                            result = {
                                "image_url": photo_url,
                                "thumbnail_url": f"{p.get('prefix')}300x300{p.get('suffix')}",
                                "source": "foursquare",
                                "source_page": f"https://foursquare.com/v/{results[0].get('fsq_id')}",
                                "verified": True
                            }
                            self._set_cache(cache_key, result)
                            return result
        except Exception:
            pass

        self._set_cache(cache_key, None)
        return None

    async def resolve_place_image(
        self,
        place_name: str,
        category: str = "attraction",
        location: str = "",
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        google_photos: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Main image resolution pipeline respecting priority:
        1. Google Place Photos
        2. Wikipedia / Wikimedia Landmark Photo
        3. Foursquare Photo
        4. None (Fallback)
        """
        # 1. Google Place Photo if available
        if google_photos and len(google_photos) > 0:
            return {
                "image_url": google_photos[0],
                "photos": google_photos,
                "source": "google",
                "verified": True
            }

        # 2. Wikipedia / Wikimedia for attractions, landmarks, monuments, parks, destinations
        wiki_res = await self.resolve_wikipedia_image(place_name, location)
        if wiki_res:
            return wiki_res

        # 3. Foursquare for dining, hotels, and business places
        if category in ["hotel", "restaurant", "activity"]:
            fsq_res = await self.resolve_foursquare_image(place_name, lat, lon)
            if fsq_res:
                return fsq_res

        return None


# Singleton instance
image_provider = ImageProvider()
