import asyncio
import re
import sys
import httpx

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

NON_LANDMARK_REGEX = re.compile(
    r"\b(battle of|siege of|rebellion|massacre|famine|election|treaty of|timeline of|"
    r"railway station|station\b|subway|metro station|airport|bombing|incident|scandal|"
    r"highway|motorway|expressway|treaty|history of|demographics of|economy of|geography of|"
    r"olympics|championship|games\b|cup\b|attack|strikes?)\b",
    re.IGNORECASE
)

def classify_title(title: str) -> str:
    t = title.lower()
    if any(k in t for k in ["museum", "gallery", "art center", "exhibition"]):
        return "museum"
    if any(k in t for k in ["palace", "castle", "fort", "temple", "shrine", "cathedral", "church", "basilica", "mosque", "tomb", "monument", "memorial", "ruins", "gate"]):
        return "historic"
    if any(k in t for k in ["park", "garden", "nature reserve", "botanical", "sanctuary"]):
        return "park"
    if any(k in t for k in ["theatre", "theater", "opera", "zoo", "aquarium", "theme park", "amusement"]):
        return "activity"
    if any(k in t for k in ["hotel", "resort", "inn\b"]):
        return "hotel"
    if any(k in t for k in ["restaurant", "cafe", "bistro"]):
        return "restaurant"
    return "attraction"

async def test_geo(city, lat, lon):
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "geosearch",
        "gscoord": f"{lat}|{lon}",
        "gsradius": 8000,
        "gslimit": 30,
        "format": "json"
    }
    async with httpx.AsyncClient(timeout=8.0, headers={"User-Agent": "TravelTrack/1.0"}) as client:
        r = await client.get(url, params=params)
        items = r.json().get("query", {}).get("geosearch", [])
        valid = []
        for it in items:
            title = it["title"]
            if NON_LANDMARK_REGEX.search(title):
                continue
            if title.lower() == city.lower():
                continue
            cat = classify_title(title)
            valid.append((title, cat, it["lat"], it["lon"]))
        print(f"=== {city} === Found {len(valid)} landmarks:")
        for t, c, la, lo in valid[:8]:
            print(f"  - {t} [{c}] ({la}, {lo})")

async def main():
    await test_geo("Tokyo", 35.6768, 139.7638)
    await test_geo("Kyoto", 35.0116, 135.7681)
    await test_geo("Paris", 48.8566, 2.3522)
    await test_geo("Delhi", 28.6139, 77.2090)

asyncio.run(main())
