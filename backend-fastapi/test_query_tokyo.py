import asyncio
import httpx
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from app.services.explore.overpass import overpass_service

endpoints = [
    'https://overpass.osm.ch/api/interpreter',
    'https://overpass.kumi.systems/api/interpreter',
    'https://overpass-api.de/api/interpreter',
    'https://lz4.overpass-api.de/api/interpreter',
    'https://z.overpass-api.de/api/interpreter',
]

q = overpass_service._build_overpass_query(35.6768601, 139.7638947, 'all', 5500)

async def test():
    async with httpx.AsyncClient(timeout=10.0, headers={'User-Agent': 'TravelTrack-App/5.0'}) as client:
        for ep in endpoints:
            try:
                t0 = asyncio.get_event_loop().time()
                r = await client.post(ep, data={'data': q})
                dt = asyncio.get_event_loop().time() - t0
                print(f'{ep} -> status {r.status_code}, time: {dt:.2f}s, len: {len(r.text)}')
                if r.status_code == 200:
                    els = r.json().get('elements', [])
                    print(f'   elements: {len(els)}')
                    for el in els[:5]:
                        print('    -', el.get('tags', {}).get('name'))
            except Exception as e:
                print(f'{ep} -> EXCEPTION: {type(e).__name__} {e}')

asyncio.run(test())
