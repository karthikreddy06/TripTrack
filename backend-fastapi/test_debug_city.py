import asyncio
import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.abspath("backend-fastapi"))

from app.services.explore.nominatim import nominatim_service
from app.services.explore.overpass import overpass_service
from app.services.explore.provider import explore_provider

async def debug_tokyo():
    print("--- 1. Nominatim Geocode Tokyo ---")
    geo = await nominatim_service.geocode("Tokyo")
    print(f"Geo: {geo.get('name')} at ({geo.get('lat')}, {geo.get('lon')})")
    
    if geo:
        print("\n--- 2. Overpass Discover Places for Tokyo (radius 5000) ---")
        raw = await overpass_service.discover_places(lat=geo["lat"], lon=geo["lon"], category="all", radius=5000)
        print(f"Overpass raw count: {len(raw)}")
        for idx, r in enumerate(raw[:8], 1):
            print(f"  {idx}. {r.get('name')} | category: {r.get('category')}")
            
        print("\n--- 3. Full search_places for Tokyo ---")
        res = await explore_provider.search_places("Tokyo", category="all", limit=8)
        places = res.get("places", [])
        print(f"Total results: {len(places)}")
        for idx, p in enumerate(places, 1):
            print(f"  {idx}. {p.get('name')} | Score: {p.get('travel_score'):.1f} | Category: {p.get('category')}")

if __name__ == "__main__":
    asyncio.run(debug_tokyo())
