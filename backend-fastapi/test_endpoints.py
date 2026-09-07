import asyncio
import httpx
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mirrors = [
    'https://overpass-api.de/api/interpreter',
    'https://lz4.overpass-api.de/api/interpreter',
    'https://z.overpass-api.de/api/interpreter',
    'https://overpass.kumi.systems/api/interpreter',
    'https://maps.mail.ru/osm/tools/overpass/api/interpreter',
    'https://overpass.openstreetmap.ru/api/interpreter',
    'https://overpass.osm.ch/api/interpreter',
    'https://overpass.private.coffee/api/interpreter',
    'https://overpass.nchc.org.tw/api/interpreter',
]

test_q = '[out:json][timeout:10];(node["tourism"="attraction"](around:3000,35.6768,139.7638););out 5;'

async def test_mirrors():
    async with httpx.AsyncClient(timeout=8.0, headers={'User-Agent': 'TravelTrack-App/5.0'}) as client:
        for m in mirrors:
            try:
                t0 = asyncio.get_event_loop().time()
                r = await client.post(m, data={'data': test_q})
                dt = asyncio.get_event_loop().time() - t0
                print(f'{m} -> status {r.status_code}, time: {dt:.2f}s, len: {len(r.text)}')
                if r.status_code == 200:
                    print('   elements:', len(r.json().get('elements', [])))
            except Exception as e:
                print(f'{m} -> EXCEPTION: {type(e).__name__} {e}')

asyncio.run(test_mirrors())
