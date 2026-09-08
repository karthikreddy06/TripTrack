import httpx
import json
import time

BASE_URL = "http://localhost:8000/api"

def test_full_flow():
    print("==================================================")
    print("STARTING FULL END-TO-END VERIFICATION")
    print("==================================================")

    with httpx.Client(timeout=15.0) as client:
        # 1. Health check
        print("\n1. Testing Health Endpoint...")
        res = client.get(f"{BASE_URL}/health")
        print(f"Status: {res.status_code}, Body: {res.json()}")
        assert res.status_code == 200
        assert res.json().get("status") == "healthy"
        print("PASS: Backend is healthy and connected to MongoDB Atlas.")

        # 2. Register / Login User
        print("\n2. Testing Authentication...")
        test_email = f"e2e_tester_{int(time.time())}@traveltrack.app"
        test_password = "SecurePassword123!"
        reg_res = client.post(f"{BASE_URL}/users/register", json={
            "name": "E2E Tester",
            "email": test_email,
            "password": test_password
        })
        print(f"Register status: {reg_res.status_code}")
        assert reg_res.status_code == 201

        login_res = client.post(f"{BASE_URL}/users/login", json={
            "email": test_email,
            "password": test_password
        })
        print(f"Login status: {login_res.status_code}")
        assert login_res.status_code == 200
        login_data = login_res.json()
        token = login_data["access_token"]
        user_id = login_data.get("user_id") or login_data.get("user", {}).get("user_id")
        headers = {"Authorization": f"Bearer {token}"}
        print(f"PASS: Logged in successfully. User ID: {user_id}")

        # 3. Wishlist with Object location (Root Cause 1)
        print("\n3. Testing Wishlist Creation with Object Location (Dict & String)...")
        dict_location_payload = {
            "place_id": "osm_node_12345678",
            "name": "Charminar Monument",
            "category": "historic",
            "location": {"lat": 17.3616, "lon": 78.4747, "address": "Charminar Rd, Old City, Hyderabad"},
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/7/71/Charminar_Hyderabad_1.jpg",
            "rating": 4.8,
            "description": "Iconic 16th-century mosque and landmark.",
            "metadata": {"lat": 17.3616, "lon": 78.4747, "provider_id": "osm/node/12345678"}
        }
        wish_res = client.post(f"{BASE_URL}/wishlist/", json=dict_location_payload, headers=headers)
        print(f"Wishlist POST status: {wish_res.status_code}")
        if wish_res.status_code != 201:
            print(f"Wishlist POST failed response: {wish_res.text}")
        assert wish_res.status_code == 201
        wish_item = wish_res.json()
        wishlist_id = wish_item["_id"]
        print(f"PASS: Wishlist created with object location. Saved ID: {wishlist_id}")

        # 4. Check Wishlist Saved
        print("\n4. Testing Wishlist Check Saved Endpoint...")
        check_res = client.get(f"{BASE_URL}/wishlist/check/osm_node_12345678", headers=headers)
        assert check_res.status_code == 200
        assert check_res.json()["is_saved"] is True
        print(f"PASS: Wishlist check confirmed place is saved: {check_res.json()}")

        # 5. Retrieve Wishlist List
        print("\n5. Testing Wishlist Retrieval Endpoint...")
        get_wish_res = client.get(f"{BASE_URL}/wishlist/", headers=headers)
        assert get_wish_res.status_code == 200
        items = get_wish_res.json()
        assert len(items) >= 1
        assert items[0]["place_id"] == "osm_node_12345678"
        assert isinstance(items[0]["location"], str)
        print(f"PASS: Wishlist retrieved items successfully. Count: {len(items)}")

        # 6. Wishlist Deletion
        print("\n6. Testing Wishlist Deletion Endpoint...")
        del_res = client.delete(f"{BASE_URL}/wishlist/{wishlist_id}", headers=headers)
        assert del_res.status_code == 200
        check_again = client.get(f"{BASE_URL}/wishlist/check/osm_node_12345678", headers=headers)
        assert check_again.json()["is_saved"] is False
        print("PASS: Wishlist item deleted and confirmed removed.")

        # 7. Add to Trip Flow (Root Cause 4)
        print("\n7. Testing Add to Trip & Itinerary Persistence...")
        trip_res = client.post(f"{BASE_URL}/trips/", json={
            "user_id": user_id,
            "destination": "Hyderabad",
            "title": "Hyderabad Heritage Tour",
            "start_date": "2026-10-10",
            "end_date": "2026-10-15",
            "budget": 1500.0,
            "travelers": 2,
            "description": "Exploring Golconda, Charminar, and Chowmahalla Palace."
        }, headers=headers)
        print(f"Create Trip Status: {trip_res.status_code}")
        assert trip_res.status_code == 201
        trip_id = trip_res.json()["trip_id"]

        act_res = client.post(f"{BASE_URL}/itinerary/", json={
            "trip_id": trip_id,
            "day_number": 1,
            "date": "2026-10-10",
            "time": "10:00 AM",
            "title": "Visit Golconda Fort",
            "location": "Golconda, Hyderabad",
            "description": "Historic fortress complex with acoustic architecture.",
            "cost": 25.0,
            "notes": "Added from Explore",
            "place_id": "osm_way_987654",
            "category": "historic",
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/golconda.jpg"
        }, headers=headers)
        print(f"Create Activity Status: {act_res.status_code}")
        assert act_res.status_code == 201

        # Verify Activity in MongoDB
        itin_res = client.get(f"{BASE_URL}/itinerary/trip/{trip_id}", headers=headers)
        assert itin_res.status_code == 200
        activities = itin_res.json()
        assert len(activities) >= 1
        assert activities[0]["title"] == "Visit Golconda Fort"
        assert activities[0]["place_id"] == "osm_way_987654"
        print(f"PASS: Itinerary activity created and persisted in MongoDB. Count: {len(activities)}")

        # 8. Dynamic Place Details (Root Cause 3)
        print("\n8. Testing Dynamic Place Details by ID...")
        # Test Place Details for Wikipedia article ID
        wiki_place_res = client.get(f"{BASE_URL}/explore/place/wiki_221151") # Charminar pageid on Wikipedia
        print(f"Wiki place details status: {wiki_place_res.status_code}")
        assert wiki_place_res.status_code == 200
        place_obj = wiki_place_res.json().get("place")
        assert place_obj is not None
        assert "name" in place_obj
        print(f"PASS: Retrieved place by Wikipedia ID: {place_obj.get('name')}")

        # Test Explore Search
        print("\n9. Testing Explore Search...")
        search_res = client.get(f"{BASE_URL}/explore/search", params={"q": "Paris", "category": "all"})
        print(f"Search status: {search_res.status_code}")
        assert search_res.status_code == 200
        places = search_res.json().get("places", [])
        print(f"PASS: Explore search returned {len(places)} verified places for Paris.")

        print("\n==================================================")
        print("ALL END-TO-END VERIFICATION CHECKS PASSED (100%)")
        print("==================================================")

if __name__ == "__main__":
    test_full_flow()
