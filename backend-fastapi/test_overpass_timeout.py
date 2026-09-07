import asyncio
import httpx
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

async def test_overpass_query():
    endpoints = [
        "https://overpass-api.de/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    ]
    
    # Fast, targeted travel query: avoids scanning 50,000 restaurants in Tokyo
    query = """[out:json][timeout:10];
(
  node["tourism"~"attraction|museum|gallery|viewpoint|theme_park|zoo"](around:5000,35.6768,139.7638);
  way["tourism"~"attraction|museum|gallery|viewpoint|theme_park|zoo"](around:5000,35.6768,139.7638);
  node["historic"~"monument|memorial|castle|fort|palace|ruins|heritage|city_gate|tomb"](around:5000,35.6768,139.7638);
  way["historic"~"monument|memorial|castle|fort|palace|ruins|heritage|archaeological_site|city_gate|tomb"](around:5000,35.6768,139.7638);
  node["leisure"~"park|garden|nature_reserve"](around:5000,35.6768,139.7638);
);
out center tags 40;
"""
    headers = {
        "User-Agent": "TravelTrack-App/5.0 (https://triptrack-frontend.onrender.com; contact: info@triptrack.app)",
        "Accept": "application/json",
    }
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=3.0)) as client:
        for ep in endpoints:
            print(f"Trying endpoint: {ep}...")
            try:
                res = await client.post(ep, data={"data": query}, headers=headers)
                print(f"Status: {res.status_code}")
                if res.status_code == 200:
                    data = res.json()
                    elements = data.get("elements", [])
                    print(f"Got {len(elements)} elements from {ep}!")
                    for idx, el in enumerate(elements[:8], 1):
                        tags = el.get("tags", {})
                        name = tags.get("name:en") or tags.get("name") or tags.get("int_name")
                        print(f"  {idx}. {name} | tags: {list(tags.keys())}")
                    break
            except Exception as e:
                print(f"Error on {ep}: {type(e).__name__}: {repr(e)}")

if __name__ == "__main__":
    asyncio.run(test_overpass_query())
