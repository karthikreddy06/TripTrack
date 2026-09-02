import sys
import uuid
from bson import ObjectId
from starlette.testclient import TestClient

from app.main import app
from app.database.mongodb import client, DATABASE_NAME, users_collection, trips_collection, itineraries_collection, expenses_collection

def run_tests():
    print("==================================================")
    print("STARTING TRAVELTRACK BACKEND TEST SUITE")
    print("==================================================")

    test_client = TestClient(app)

    # 1. Health Check
    print("\n[TEST 1] Checking /health endpoint...")
    res = test_client.get("/health")
    print("Health response:", res.status_code, res.json())
    assert res.status_code in [200, 503], f"Unexpected health status: {res.status_code}"

    # Generate unique test user
    rand_id = uuid.uuid4().hex[:8]
    test_email = f"testuser_{rand_id}@example.com"
    test_password = "SecurePassword123!"
    test_name = "Test Travel Explorer"

    # 2. User Registration
    print(f"\n[TEST 2] Registering user {test_email}...")
    reg_payload = {
        "name": test_name,
        "email": test_email,
        "password": test_password
    }
    res = test_client.post("/users/register", json=reg_payload)
    print("Register response:", res.status_code, res.json())
    assert res.status_code == 201, f"Registration failed: {res.text}"
    user_id = res.json()["user_id"]
    assert user_id, "user_id not returned"

    # 3. Duplicate User Registration (Conflict 409)
    print("\n[TEST 3] Testing duplicate email registration (expect 409)...")
    res = test_client.post("/users/register", json=reg_payload)
    print("Duplicate register response:", res.status_code, res.json())
    assert res.status_code == 409, f"Expected 409 Conflict, got {res.status_code}"

    # 4. Login (Wrong Password - 401)
    print("\n[TEST 4] Testing invalid login (expect 401)...")
    res = test_client.post("/users/login", json={"email": test_email, "password": "WrongPassword"})
    print("Invalid login response:", res.status_code)
    assert res.status_code == 401, f"Expected 401, got {res.status_code}"

    # 5. Login (Success - 200)
    print("\n[TEST 5] Logging in with valid credentials...")
    res = test_client.post("/users/login", json={"email": test_email, "password": test_password})
    print("Login response:", res.status_code)
    assert res.status_code == 200, f"Login failed: {res.text}"
    token_data = res.json()
    token = token_data["access_token"]
    assert token, "Access token missing"
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 6. Profile Operations
    print("\n[TEST 6] Testing profile endpoints (/users/me & /users/profile)...")
    res = test_client.get("/users/me", headers=auth_headers)
    print("Get /users/me response:", res.status_code, res.json().get("name"))
    assert res.status_code == 200
    assert res.json()["email"] == test_email

    # Update profile
    res = test_client.put(
        "/users/profile",
        headers=auth_headers,
        json={"name": "Updated Explorer", "bio": "Passionate world wanderer.", "travel_preferences": ["Nature", "Food"]}
    )
    print("Update profile response:", res.status_code, res.json())
    assert res.status_code == 200

    # Verify updated profile
    res = test_client.get("/users/me", headers=auth_headers)
    assert res.json()["name"] == "Updated Explorer"
    assert res.json()["bio"] == "Passionate world wanderer."
    assert "Nature" in res.json()["travel_preferences"]

    # 7. Password Change
    print("\n[TEST 7] Testing password change...")
    new_password = "BrandNewPassword456!"
    res = test_client.put(
        "/users/change-password",
        headers=auth_headers,
        json={"current_password": test_password, "new_password": new_password}
    )
    print("Change password response:", res.status_code, res.json())
    assert res.status_code == 200

    # Verify login with new password
    res = test_client.post("/users/login", json={"email": test_email, "password": new_password})
    assert res.status_code == 200, "Login with new password failed"
    token = res.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 8. Trip CRUD
    print("\n[TEST 8] Testing Trip CRUD...")
    trip_payload = {
        "user_id": user_id,
        "destination": "Kyoto, Japan",
        "title": "Autumn in Kyoto",
        "start_date": "2026-10-10",
        "end_date": "2026-10-17",
        "status": "planned",
        "budget": 3500.0,
        "description": "Temples, gardens, and culinary explorations.",
        "travelers": 2,
        "notes": "Book shinkansen tickets in advance."
    }
    res = test_client.post("/trips/", headers=auth_headers, json=trip_payload)
    print("Create trip response:", res.status_code, res.json())
    assert res.status_code == 201
    trip_id = res.json()["trip_id"]

    # Get user trips
    res = test_client.get(f"/trips/{user_id}", headers=auth_headers)
    print("Get trips response:", res.status_code, f"Total trips: {len(res.json())}")
    assert res.status_code == 200
    assert len(res.json()) >= 1

    # Get single trip
    res = test_client.get(f"/trips/single/{trip_id}", headers=auth_headers)
    print("Get single trip response:", res.status_code, res.json().get("destination"))
    assert res.status_code == 200
    assert res.json()["destination"] == "Kyoto, Japan"
    assert res.json()["title"] == "Autumn in Kyoto"

    # Update trip
    res = test_client.put(
        f"/trips/{trip_id}",
        headers=auth_headers,
        json={"status": "ongoing", "budget": 3800.0}
    )
    print("Update trip response:", res.status_code, res.json())
    assert res.status_code == 200

    # 9. Itinerary CRUD
    print("\n[TEST 9] Testing Itinerary CRUD...")
    activity_1 = {
        "trip_id": trip_id,
        "day_number": 1,
        "date": "2026-10-10",
        "time": "09:00 AM",
        "title": "Fushimi Inari Shrine Hike",
        "location": "Fushimi Ward, Kyoto",
        "description": "Walk through the iconic thousand vermilion torii gates.",
        "cost": 0.0,
        "notes": "Go early to avoid crowds."
    }
    res = test_client.post("/itinerary/", headers=auth_headers, json=activity_1)
    print("Create activity 1 response:", res.status_code, res.json())
    assert res.status_code == 201
    act1_id = res.json()["activity_id"]

    activity_2 = {
        "trip_id": trip_id,
        "day_number": 1,
        "date": "2026-10-10",
        "time": "12:30 PM",
        "title": "Nishiki Market Food Walk",
        "location": "Nakagyo Ward, Kyoto",
        "description": "Sample skewers, matcha sweets, and seasonal seafood.",
        "cost": 45.0
    }
    res = test_client.post("/itinerary/", headers=auth_headers, json=activity_2)
    assert res.status_code == 201
    act2_id = res.json()["activity_id"]

    # Get chronological activities for trip
    res = test_client.get(f"/itinerary/trip/{trip_id}", headers=auth_headers)
    print("Get activities response:", res.status_code, f"Activities count: {len(res.json())}")
    assert res.status_code == 200
    assert len(res.json()) == 2
    assert res.json()[0]["time"] == "09:00 AM"

    # Update activity
    res = test_client.put(
        f"/itinerary/{act1_id}",
        headers=auth_headers,
        json={"cost": 10.0, "notes": "Bought souvenir amulet."}
    )
    assert res.status_code == 200

    # 10. Expense CRUD & Budget Analytics
    print("\n[TEST 10] Testing Expenses CRUD & Budget Analytics...")
    exp_1 = {
        "trip_id": trip_id,
        "category": "Accommodation",
        "amount": 1200.0,
        "date": "2026-10-10",
        "description": "Traditional Ryokan in Gion"
    }
    res = test_client.post("/expenses/", headers=auth_headers, json=exp_1)
    print("Create expense 1 response:", res.status_code, res.json())
    assert res.status_code == 201
    exp1_id = res.json()["expense_id"]

    exp_2 = {
        "trip_id": trip_id,
        "category": "Food",
        "amount": 250.0,
        "date": "2026-10-11",
        "description": "Kaiseki Dinner Experience"
    }
    res = test_client.post("/expenses/", headers=auth_headers, json=exp_2)
    assert res.status_code == 201

    exp_3 = {
        "trip_id": trip_id,
        "category": "Transport",
        "amount": 180.0,
        "date": "2026-10-10",
        "description": "JR Kansai Area Pass"
    }
    res = test_client.post("/expenses/", headers=auth_headers, json=exp_3)
    assert res.status_code == 201

    # Check trip budget summary
    res = test_client.get(f"/expenses/trip/{trip_id}", headers=auth_headers)
    print("Get trip expenses response:", res.status_code)
    assert res.status_code == 200
    summary = res.json()["summary"]
    print("Budget Summary:", summary)
    assert summary["budget"] == 3800.0
    assert summary["total_spent"] == 1630.0
    assert summary["remaining_budget"] == 2170.0
    assert summary["by_category"]["Accommodation"] == 1200.0
    assert summary["by_category"]["Food"] == 250.0
    assert summary["by_category"]["Transport"] == 180.0

    # Check user expense summary
    res = test_client.get(f"/expenses/user/{user_id}/summary", headers=auth_headers)
    print("User expense summary response:", res.status_code, res.json())
    assert res.status_code == 200
    assert res.json()["total_spent"] == 1630.0

    # 11. AI Trip Planner & AI Budget Assistant
    print("\n[TEST 11] Testing AI Trip Planner & AI Budget Assistant...")
    ai_plan_req = {
        "destination": "Kyoto, Japan",
        "days": 3,
        "start_date": "2026-10-10",
        "travelers": 2,
        "budget": 3800.0,
        "interests": ["Culture", "Food", "Nature"],
        "travel_style": "Balanced"
    }
    res = test_client.post("/ai/plan-trip", headers=auth_headers, json=ai_plan_req)
    print("AI Plan response:", res.status_code, "Days planned:", len(res.json().get("itinerary", [])))
    assert res.status_code == 200
    assert len(res.json()["itinerary"]) == 3
    assert len(res.json()["packing_list"]) > 0
    assert len(res.json()["travel_tips"]) > 0

    # AI Budget Advice
    res = test_client.post("/ai/budget-advice", headers=auth_headers, json={"trip_id": trip_id})
    print("AI Budget advice response:", res.status_code, "Status:", res.json().get("status"))
    assert res.status_code == 200
    assert res.json()["status"] in ["on_track", "caution", "overbudget"]
    assert len(res.json()["saving_tips"]) > 0

    # 12. Security & Forbidden Access Checks
    print("\n[TEST 12] Testing Authorization and Security Boundaries...")
    # Attempting to access another user's trips with different user ID
    fake_user_id = "507f1f77bcf86cd799439011"
    res = test_client.get(f"/trips/{fake_user_id}", headers=auth_headers)
    print("Access other user's trips response:", res.status_code)
    assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}"

    # Missing / Invalid token
    res = test_client.get(f"/trips/{user_id}", headers={"Authorization": "Bearer invalid_token_abc"})
    print("Invalid token response:", res.status_code)
    assert res.status_code == 401, f"Expected 401 Unauthorized, got {res.status_code}"

    # 14. Explore & Travel Discovery
    print("\n[TEST 14] Testing Explore Discovery Endpoints...")
    res = test_client.get("/explore/featured")
    print("Explore featured response:", res.status_code, "Count:", len(res.json()))
    assert res.status_code == 200
    assert len(res.json()) >= 1

    # Search Goa
    res = test_client.get("/explore/search?q=goa&category=all")
    print("Explore search response:", res.status_code, "Results:", res.json().get("total_results"))
    assert res.status_code == 200
    assert res.json()["total_results"] > 0

    # Destination details
    res = test_client.get("/explore/destinations/goa")
    print("Destination details response:", res.status_code, res.json().get("destination"))
    assert res.status_code == 200
    assert res.json()["destination"] == "Goa"

    # Place details
    res = test_client.get("/explore/places/goa-baga-beach")
    print("Place details response:", res.status_code, res.json()["place"]["name"])
    assert res.status_code == 200
    assert res.json()["place"]["name"] == "Baga Beach"

    # 15. Wishlist CRUD
    print("\n[TEST 15] Testing Wishlist Operations...")
    wishlist_item_1 = {
        "place_id": "goa-baga-beach",
        "name": "Baga Beach",
        "category": "attraction",
        "location": "North Goa, Goa",
        "image_url": "https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?w=800",
        "rating": 4.5,
        "description": "Famous beach destination with water sports and shacks.",
        "metadata": {"lat": 15.5553, "lon": 73.7517}
    }
    res = test_client.post("/wishlist/", headers=auth_headers, json=wishlist_item_1)
    print("Add to wishlist response:", res.status_code, res.json().get("name"))
    assert res.status_code in [200, 201]
    wishlist_id = res.json()["_id"]

    # Check place in wishlist
    res = test_client.get("/wishlist/check/goa-baga-beach", headers=auth_headers)
    print("Wishlist check response:", res.status_code, res.json())
    assert res.status_code == 200
    assert res.json()["is_saved"] is True
    assert res.json()["wishlist_id"] == wishlist_id

    # 16. Wishlist Duplicate Prevention & Deletion
    print("\n[TEST 16] Testing Wishlist Duplicate Prevention & Deletion...")
    # Attempt duplicate addition
    res = test_client.post("/wishlist/", headers=auth_headers, json=wishlist_item_1)
    assert res.status_code in [200, 201]

    # Verify count is still 1
    res = test_client.get("/wishlist/", headers=auth_headers)
    print("Get wishlist response:", res.status_code, "Count:", len(res.json()))
    assert res.status_code == 200
    assert len(res.json()) == 1

    # Delete wishlist item
    res = test_client.delete(f"/wishlist/{wishlist_id}", headers=auth_headers)
    print("Delete wishlist item response:", res.status_code, res.json())
    assert res.status_code == 200

    # Verify check returns false now
    res = test_client.get("/wishlist/check/goa-baga-beach", headers=auth_headers)
    assert res.json()["is_saved"] is False

    # 17. Cascade Deletion Check
    print("\n[TEST 17] Testing Cascade Cleanup on Trip Delete...")
    res = test_client.delete(f"/trips/{trip_id}", headers=auth_headers)
    print("Delete trip response:", res.status_code, res.json())
    assert res.status_code == 200

    # Confirm activities deleted
    act_count = itineraries_collection.count_documents({"trip_id": trip_id})
    assert act_count == 0, f"Expected 0 cascade activities, found {act_count}"

    # Confirm expenses deleted
    exp_count = expenses_collection.count_documents({"trip_id": trip_id})
    assert exp_count == 0, f"Expected 0 cascade expenses, found {exp_count}"

    # Cleanup test user
    users_collection.delete_one({"_id": ObjectId(user_id)})
    print("Cleaned up test user.")

    print("\n==================================================")
    print("ALL 17 BACKEND TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
