import httpx
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000/api"

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    import math
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def run_tests():
    print("=" * 60)
    print("TRAVELTRACK EXPLORE — GLOBAL DYNAMIC & TYPO-TOLERANT VERIFICATION")
    print("=" * 60)

    # 1. Test Autocomplete Suggestions
    typo_tests = [
        ("kolk", "Kolkata"),
        ("kolkata", "Kolkata"),
        ("kolkota", "Kolkata"),
        ("hyderbad", "Hyderabad"),
        ("bengaluru", "Bengaluru"),
        ("banglore", "Bengaluru"),
        ("pariss", "Paris"),
        ("New Yrok", "New York"),
        ("Eiffel Tower", "Eiffel"),
        ("Charminar", "Charminar"),
    ]

    print("\n--- PHASE 1: AUTOCOMPLETE SUGGESTIONS & TYPO TOLERANCE ---")
    for query, expected_keyword in typo_tests:
        t0 = time.time()
        r = httpx.get(f"{BASE_URL}/explore/suggestions", params={"q": query, "limit": 4}, timeout=8.0)
        dur = round(time.time() - t0, 2)
        assert r.status_code == 200, f"Failed suggestions for '{query}': {r.status_code}"
        sugs = r.json()
        assert len(sugs) > 0, f"No suggestions returned for '{query}'"
        
        top = sugs[0]
        name = top.get("name", "")
        subtitle = top.get("subtitle", "")
        is_dest = top.get("is_destination", False)
        
        match_found = any(expected_keyword.lower() in s.get("name", "").lower() for s in sugs)
        status_icon = "✓" if match_found else "✗"
        print(f"[{status_icon}] Query '{query:<12}' -> Top: '{name}' ({subtitle}) [Dest: {is_dest}] in {dur}s")
        assert match_found, f"Expected '{expected_keyword}' in suggestions for '{query}', got: {[s['name'] for s in sugs]}"

    # 2. Test Distance & Boundary Validation for Misspelled Searches
    print("\n--- PHASE 2: LOCATION VALIDATION & ZERO CROSS-CITY CONTAMINATION ---")
    location_searches = [
        ("kolkota", "Kolkata", 22.57, 88.36, 28.0),
        ("hyderbad", "Hyderabad", 17.36, 78.47, 28.0),
        ("banglore", "Bengaluru", 12.97, 77.59, 28.0),
        ("pariss", "Paris", 48.85, 2.34, 28.0),
        ("New Yrok", "New York", 40.71, -74.00, 28.0),
    ]

    for query, dest_name, center_lat, center_lon, max_dist_km in location_searches:
        t0 = time.time()
        r = httpx.get(f"{BASE_URL}/explore/search", params={"q": query, "limit": 12}, timeout=25.0)
        dur = round(time.time() - t0, 2)
        assert r.status_code == 200, f"Search failed for '{query}': {r.status_code}"
        data = r.json()
        places = data.get("places", [])
        dest_info = data.get("destination_info") or {}
        resolved_dest = dest_info.get("destination", "")

        print(f"\n[✓] Search '{query}' -> Resolved Destination: '{resolved_dest}' ({dest_info.get('country')}) in {dur}s")
        print(f"    Total places returned: {len(places)}")

        # Verify no places are outside max_dist_km
        for p in places:
            p_lat = p.get("lat")
            p_lon = p.get("lon")
            if p_lat is not None and p_lon is not None:
                dist = haversine_km(center_lat, center_lon, p_lat, p_lon)
                assert dist <= max_dist_km, f"CRITICAL: Place '{p['name']}' at ({p_lat}, {p_lon}) is {round(dist, 1)}km from {dest_name}, exceeds {max_dist_km}km!"
        
        for idx, p in enumerate(places[:3]):
            print(f"    ({idx+1}) {p['name']} [{p['category']}] -> {p['address']}")

    # 3. Test Specific Landmark Searches
    print("\n--- PHASE 3: SPECIFIC LANDMARK SEARCH & CANONICAL POI DETAILS ---")
    landmarks = ["Charminar", "Eiffel Tower"]
    for lm in landmarks:
        t0 = time.time()
        r = httpx.get(f"{BASE_URL}/explore/search", params={"q": lm, "limit": 6}, timeout=10.0)
        dur = round(time.time() - t0, 2)
        assert r.status_code == 200, f"Search failed for landmark '{lm}'"
        data = r.json()
        places = data.get("places", [])
        assert len(places) > 0, f"No places returned for landmark '{lm}'"
        top = places[0]
        print(f"[✓] Landmark '{lm}' in {dur}s -> Top Result: '{top['name']}' [{top['category']}] @ ({top['lat']}, {top['lon']})")

        # Test place details endpoint
        p_id = top["id"]
        rd = httpx.get(f"{BASE_URL}/explore/places/{p_id}", timeout=8.0)
        assert rd.status_code == 200, f"Place detail failed for '{p_id}'"
        p_data = rd.json().get("place", {})
        print(f"    -> /explore/places/{p_id} returned: '{p_data['name']}' (Nearby count: {len(rd.json().get('nearby_places', []))})")

    print("\n" + "=" * 60)
    print("ALL EXPLORE SEARCH, TYPO TOLERANCE & VALIDATION TESTS PASSED (100%)")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
