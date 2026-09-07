import asyncio
import httpx
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

async def test_wiki_geo(city_name, lat, lon):
    url = 'https://en.wikipedia.org/w/api.php'
    params = {
        'action': 'query',
        'list': 'geosearch',
        'gscoord': f'{lat}|{lon}',
        'gsradius': 8000,
        'gslimit': 25,
        'format': 'json'
    }
    headers = {'User-Agent': 'TravelTrack/1.0'}
    async with httpx.AsyncClient(timeout=8.0, headers=headers) as client:
        r = await client.get(url, params=params)
        items = r.json().get('query', {}).get('geosearch', [])
        print(f'=== {city_name} (coords: {lat}, {lon}) ===')
        print(f'GeoSearch items count: {len(items)}')
        for it in items[:8]:
            print(f" - {it['title']} (pageid: {it['pageid']}, dist: {it['dist']}m)")

async def main():
    await test_wiki_geo('Tokyo', 35.6768, 139.7638)
    await test_wiki_geo('Kyoto', 35.0116, 135.7681)
    await test_wiki_geo('Paris', 48.8566, 2.3522)
    await test_wiki_geo('Mumbai', 18.9220, 72.8347)

asyncio.run(main())
