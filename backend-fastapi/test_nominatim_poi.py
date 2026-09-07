import asyncio
import httpx
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Tokyo bbox: 35.6, 139.7, 35.75, 139.85
# viewbox format in Nominatim: <left>,<top>,<right>,<bottom> = minlon,maxlat,maxlon,minlat
# For Tokyo: 139.70,35.75,139.82,35.65

async def test_nominatim_viewbox():
    headers = {'User-Agent': 'TravelTrack-Explore/4.0'}
    async with httpx.AsyncClient(timeout=8.0, headers=headers) as client:
        # 1. Search category in destination
        queries = [
            'attractions in Tokyo',
            'historic places in Tokyo',
            'museums in Tokyo',
            'parks in Tokyo',
            'tourism in Tokyo'
        ]
        for q in queries:
            r = await client.get('https://nominatim.openstreetmap.org/search', params={
                'q': q,
                'format': 'jsonv2',
                'addressdetails': 1,
                'extratags': 1,
                'namedetails': 1,
                'limit': 10
            })
            print(f'Nominatim query: {q} -> status: {r.status_code}, count: {len(r.json()) if r.status_code == 200 else 0}')
            if r.status_code == 200:
                for item in r.json()[:3]:
                    names = item.get('namedetails', {})
                    name = names.get('name:en') or names.get('int_name') or item.get('name') or item.get('display_name')
                    print(f'   - {name} ({item.get("category")}/{item.get("type")})')

        # 2. Test photon query around Tokyo coordinates
        r_ph = await client.get('https://photon.komoot.io/api/', params={
            'q': 'tourism',
            'lat': 35.6768,
            'lon': 139.7638,
            'limit': 15
        })
        print(f'Photon tourism near Tokyo -> status: {r_ph.status_code}, count: {len(r_ph.json().get("features", [])) if r_ph.status_code == 200 else 0}')
        if r_ph.status_code == 200:
            for feat in r_ph.json().get('features', [])[:5]:
                props = feat.get('properties', {})
                print(f'   - {props.get("name")} ({props.get("osm_key")}/{props.get("osm_value")})')

asyncio.run(test_nominatim_viewbox())
