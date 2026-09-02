import asyncio
import sys

sys.stdout.reconfigure(encoding="utf-8")

from app.services.explore.provider import explore_provider


async def run_explore_tests():
    print("========================================")
    print("TRAVELTRACK DYNAMIC WORLDWIDE EXPLORE TESTS")
    print("========================================")

    # 1. City / Destination Search
    test_cities = ["Kyoto", "Reykjavik", "Hyderabad"]
    for city in test_cities:
        res = await explore_provider.search_places(city, category="all", page=1, limit=5)
        places = res.get("places", [])
        dest_info = res.get("destination_info") or {}
        dest_name = dest_info.get("destination", "Unknown")
        dest_country = dest_info.get("country", "")
        print(f"[City Search] '{city}' -> Found {len(places)} places (Total: {res.get('total_results')}) | Destination: {dest_name} ({dest_country})")
        assert len(places) > 0, f"Expected places for {city}"

    # 2. Specific Landmark / Place Search
    test_landmarks = ["Eiffel Tower", "Charminar"]
    for lm in test_landmarks:
        res = await explore_provider.search_places(lm, category="all", page=1, limit=5)
        places = res.get("places", [])
        print(f"[Landmark Search] '{lm}' -> Found {len(places)} places (Total: {res.get('total_results')})")
        assert len(places) > 0, f"Expected match for landmark {lm}"
        top = places[0]
        print(f"   Top: {top.get('name')} [{top.get('category')}] - {top.get('address')[:40]}... @ ({top.get('lat')}, {top.get('lon')})")

        # 3. Place by ID resolution
        p_detail = await explore_provider.get_place_by_id(top.get("id"))
        assert p_detail and p_detail.get("place"), f"Failed to get_place_by_id for {top.get('id')}"
        print(f"   get_place_by_id({top.get('id')}) -> OK ({p_detail['place']['name']})")

    # 4. Destination Guide
    guide = await explore_provider.get_destination_details("Florence")
    assert guide and guide.get("destination"), "Expected guide for Florence"
    print(f"[Destination Guide] 'Florence' -> {guide.get('destination')} ({guide.get('country')}) | Highlights: {len(guide.get('highlights', []))}")

    print("\nALL DYNAMIC EXPLORE TESTS PASSED SUCCESSFULLY.")


if __name__ == "__main__":
    asyncio.run(run_explore_tests())
