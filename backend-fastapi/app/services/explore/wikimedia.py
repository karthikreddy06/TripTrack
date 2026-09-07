import re
import time
import urllib.parse
from typing import Dict, List, Optional, Any
import httpx

# In-memory cache for Wikimedia verified image and summary results (TTL: 24 hours)
_WIKI_CACHE: Dict[str, Dict[str, Any]] = {}
WIKI_CACHE_TTL = 86400


class WikimediaService:
    """
    Wikimedia & Wikipedia Entity Resolution Service.
    Resolves verified lead photographs, descriptions, and page links strictly tied to the canonical place entity.
    Never uses random keyword search or unverified image guessing.
    """

    def __init__(self):
        self.timeout = httpx.Timeout(1.8, connect=0.8)
        self.headers = {
            "User-Agent": "TravelTrack-App/4.0 (https://triptrack-frontend.onrender.com; contact: info@triptrack.app)"
        }

    def _get_cache(self, key: str) -> Optional[Dict[str, Any]]:
        cached = _WIKI_CACHE.get(key)
        if cached and (time.time() - cached["timestamp"]) < WIKI_CACHE_TTL:
            return cached["data"]
        return None

    def _set_cache(self, key: str, data: Optional[Dict[str, Any]]):
        _WIKI_CACHE[key] = {
            "timestamp": time.time(),
            "data": data
        }

    async def get_wikipedia_page_summary(self, page_title: str, lang: str = "en") -> Optional[Dict[str, Any]]:
        """
        Fetch summary, lead photo, and description from Wikipedia REST API for a specific article.
        """
        if not page_title:
            return None

        clean_title = page_title.replace(" ", "_").strip()
        cache_key = f"wiki_page:{lang}:{clean_title.lower()}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(clean_title)}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url, headers=self.headers)
                if res.status_code == 200:
                    data = res.json()
                    page_type = data.get("type", "")
                    if page_type not in ["disambiguation", "no-extract"]:
                        original_img = data.get("originalimage", {}).get("source")
                        thumb_img = data.get("thumbnail", {}).get("source")
                        lead_img = original_img or thumb_img

                        # Ignore icon-size svgs or flags
                        if lead_img and lead_img.endswith(".svg") and "logo" in lead_img.lower():
                            lead_img = None

                        result = {
                            "title": data.get("title"),
                            "description": data.get("extract") or data.get("description"),
                            "image_url": lead_img,
                            "image_verified": bool(lead_img),
                            "image_source": "wikipedia" if lead_img else None,
                            "image_source_url": data.get("content_urls", {}).get("desktop", {}).get("page"),
                            "wikipedia_url": data.get("content_urls", {}).get("desktop", {}).get("page"),
                        }
                        self._set_cache(cache_key, result)
                        return result
        except Exception:
            pass

        self._set_cache(cache_key, None)
        return None

    async def resolve_place_entity(
        self,
        name: str,
        category: str = "attraction",
        osm_wikipedia: Optional[str] = None,
        osm_wikidata: Optional[str] = None,
        osm_image: Optional[str] = None,
        location_hint: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve verified image & description for a place using entity tags or exact title lookup.
        """
        # 1. Check exact OSM wikipedia tag
        if osm_wikipedia:
            parts = osm_wikipedia.split(":", 1)
            if len(parts) == 2:
                lang, title = parts[0], parts[1]
                summary = await self.get_wikipedia_page_summary(title, lang=lang)
                if summary:
                    return summary
            else:
                summary = await self.get_wikipedia_page_summary(osm_wikipedia, lang="en")
                if summary:
                    return summary

        # 2. Check OSM image tag
        if osm_image and osm_image.startswith("http"):
            return {
                "title": name,
                "description": None,
                "image_url": osm_image,
                "image_verified": True,
                "image_source": "wikimedia_commons",
                "image_source_url": osm_image,
                "wikipedia_url": None,
            }

        # 3. For notable landmarks/attractions/museums, check exact page title in Wikipedia
        if category in ["attraction", "museum", "historic", "park", "destination"]:
            summary = await self.get_wikipedia_page_summary(name, lang="en")
            if summary and summary.get("image_url"):
                return summary

            # Try with location suffix (e.g. "Charminar, Hyderabad")
            if location_hint:
                loc_city = location_hint.split(",")[0].strip()
                summary_loc = await self.get_wikipedia_page_summary(f"{name}_{loc_city}", lang="en")
                if summary_loc and summary_loc.get("image_url"):
                    return summary_loc

        # If not verified, return unverified (no image)
        return {
            "title": name,
            "description": None,
            "image_url": None,
            "image_verified": False,
            "image_source": None,
            "image_source_url": None,
            "wikipedia_url": None,
        }


    async def search_places_near_coords(
        self,
        lat: float,
        lon: float,
        category: str = "all",
        radius: int = 8000,
        limit: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Dynamically discover notable cultural landmarks, museums, monuments, parks, and attractions
        around any geographic coordinates on Earth using Wikipedia Geosearch.
        """
        non_landmark_regex = re.compile(
            r"\b(battle of|siege of|rebellion|massacre|famine|election|treaty of|timeline of|"
            r"railway station|station\b|subway|metro station|airport|bombing|incident|scandal|"
            r"highway|motorway|expressway|treaty|history of|demographics of|economy of|geography of|"
            r"olympics|championship|games\b|cup\b|attack|strikes?|commune|empire|festival|"
            r"constituency|lok sabha|vidhan sabha|assembly constituency|district\b|division\b|"
            r"engineering college|medical college|university\b|high school|college of|institute of|"
            r"consulate|embassy|high commission|fire department|fire station|police department|police station|stock exchange|"
            r"municipal corporation|ministry of|department of|council\b)\b",
            re.IGNORECASE
        )

        def classify_article_title(title: str) -> str:
            t = title.lower()
            if any(k in t for k in ["museum", "gallery", "art center", "exhibition", "collection"]):
                return "museum"
            if any(k in t for k in ["palace", "castle", "fort", "temple", "shrine", "cathedral", "church", "basilica", "mosque", "tomb", "monument", "memorial", "ruins", "gate"]):
                return "historic"
            if any(k in t for k in ["park", "garden", "nature reserve", "botanical", "sanctuary", "forest"]):
                return "park"
            if any(k in t for k in ["theatre", "theater", "opera", "zoo", "aquarium", "theme park", "amusement"]):
                return "activity"
            if any(k in t for k in ["hotel", "resort", "inn\b"]):
                return "hotel"
            if any(k in t for k in ["restaurant", "cafe", "bistro", "bakery"]):
                return "restaurant"
            return "attraction"

        url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "geosearch",
            "gscoord": f"{lat}|{lon}",
            "gsradius": min(10000, max(1000, radius)),
            "gslimit": min(50, limit * 2),
            "format": "json"
        }

        results: List[Dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                res = await client.get(url, params=params)
                if res.status_code == 200:
                    data = res.json()
                    items = data.get("query", {}).get("geosearch", [])
                    for it in items:
                        title = it.get("title", "").strip()
                        if not title or non_landmark_regex.search(title):
                            continue

                        cat = classify_article_title(title)
                        p_lat = float(it.get("lat", 0.0))
                        p_lon = float(it.get("lon", 0.0))
                        pageid = it.get("pageid")

                        results.append({
                            "id": f"wiki_{pageid}",
                            "place_id": f"wiki_{pageid}",
                            "provider_id": f"wikipedia/{pageid}",
                            "name": title,
                            "category": cat,
                            "address": title,
                            "lat": p_lat,
                            "lon": p_lon,
                            "phone": None,
                            "website": None,
                            "opening_hours": None,
                            "osm_wikipedia": f"en:{title}",
                            "osm_wikidata": None,
                            "osm_image": None,
                            "tags": [cat.title(), "Wikipedia Verified"],
                            "raw_tags": {"tourism": cat, "wikipedia": f"en:{title}"}
                        })
                        if len(results) >= limit:
                            break
        except Exception:
            pass

        return results


# Singleton instance
wikimedia_service = WikimediaService()

