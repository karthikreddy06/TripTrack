import sys
import uuid
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from bson import ObjectId
from starlette.testclient import TestClient

from app.main import app
from app.auth import create_access_token
from app.database.mongodb import (
    users_collection,
    trips_collection,
    itineraries_collection,
    expenses_collection,
    wishlist_collection,
    chat_conversations_collection
)


def run_ai_agent_tests():
    print("=" * 60)
    print("STARTING REAL CONTEXT-AWARE AI TRAVEL AGENT TEST SUITE")
    print("=" * 60)

    client = TestClient(app, raise_server_exceptions=False)

    # 1. Setup two test users for authorization isolation testing
    u1_id = "507f1f77bcf86cd799439001"
    u2_id = "507f1f77bcf86cd799439002"
    t1_token = create_access_token(u1_id)
    t2_token = create_access_token(u2_id)
    conv_id = f"test_conv_{uuid.uuid4().hex[:8]}"

    # Clean previous test artifacts
    trips_collection.delete_many({"user_id": {"$in": [u1_id, u2_id]}})
    itineraries_collection.delete_many({"user_id": {"$in": [u1_id, u2_id]}})
    expenses_collection.delete_many({"user_id": {"$in": [u1_id, u2_id]}})
    wishlist_collection.delete_many({"user_id": {"$in": [u1_id, u2_id]}})
    chat_conversations_collection.delete_many({"user_id": {"$in": [u1_id, u2_id]}})

    # Create real test trip for User 1
    trip1_res = trips_collection.insert_one({
        "user_id": u1_id,
        "destination": "Hyderabad, India",
        "title": "Royal Hyderabad Odyssey",
        "start_date": "2026-10-01",
        "end_date": "2026-10-05",
        "budget": 25000.0,
        "travelers": 2,
        "status": "planned",
        "description": "Historical monuments and culinary exploration."
    })
    trip1_id = str(trip1_res.inserted_id)

    # Add an initial expense for User 1
    expenses_collection.insert_one({
        "trip_id": trip1_id,
        "user_id": u1_id,
        "category": "Accommodation",
        "amount": 8000.0,
        "description": "Boutique Heritage Hotel",
        "date": "2026-10-01"
    })

    print(f"\n[SETUP] Seeded Trip '{trip1_id}' and expense for User 1.")

    # =============================================================
    # RULE 8 EXACT VERIFICATION TESTS
    # =============================================================

    # -------------------------------------------------------------
    # CASE 1: "heyy" -> greeting only, ZERO tool calls
    # -------------------------------------------------------------
    print("\n[CASE 1] Testing 'heyy' (pure casual greeting)...")
    res1 = client.post(
        "/ai/chat",
        headers={"Authorization": f"Bearer {t1_token}"},
        json={"message": "heyy", "conversation_id": f"conv_c1_{uuid.uuid4().hex[:6]}"}
    )
    assert res1.status_code == 200, f"Expected 200, got {res1.status_code}: {res1.text}"
    d1 = res1.json()
    assert d1["tool_called"] is None, f"Expected tool_called=None, got '{d1['tool_called']}'"
    assert len(d1.get("places", [])) == 0, f"Expected 0 places, got {len(d1.get('places', []))}"
    assert "New Delhi" not in d1["response"], "CRITICAL BUG: New Delhi assumed for 'heyy'!"
    assert "Kolkata" not in d1["response"], "Unrequested city assumed!"
    print("  [PASS] 'heyy' returned natural greeting with ZERO tool calls and NO assumed city.")

    # -------------------------------------------------------------
    # CASE 1A (REGRESSION): "get me all the places in mumbai" -> search_places for Mumbai
    # -------------------------------------------------------------
    print("\n[CASE 1A] Testing 'get me all the places in mumbai'...")
    res1a = client.post(
        "/ai/chat",
        headers={"Authorization": f"Bearer {t1_token}"},
        json={"message": "get me all the places in mumbai", "conversation_id": f"conv_mumbai_{uuid.uuid4().hex[:6]}"}
    )
    assert res1a.status_code == 200
    d1a = res1a.json()
    assert d1a["tool_called"] == "search_places", f"Expected 'search_places', got '{d1a['tool_called']}'"
    assert len(d1a.get("places", [])) > 0, "Expected places for Mumbai"
    assert "Good morning" not in d1a["response"], "CRITICAL BUG: Initial greeting returned instead of Mumbai places!"
    assert "Good afternoon" not in d1a["response"], "CRITICAL BUG: Initial greeting returned instead of Mumbai places!"
    print(f"  [PASS] 'get me all the places in mumbai' called search_places for Mumbai (found {len(d1a['places'])} places, first: '{d1a['places'][0]['name']}').")

    # -------------------------------------------------------------
    # CASE 1B (REGRESSION): "mumbai" -> search_places for Mumbai
    # -------------------------------------------------------------
    print("\n[CASE 1B] Testing single word 'mumbai'...")
    res1b = client.post(
        "/ai/chat",
        headers={"Authorization": f"Bearer {t1_token}"},
        json={"message": "mumbai", "conversation_id": f"conv_mumbai2_{uuid.uuid4().hex[:6]}"}
    )
    assert res1b.status_code == 200
    d1b = res1b.json()
    assert d1b["tool_called"] == "search_places", f"Expected 'search_places', got '{d1b['tool_called']}'"
    assert len(d1b.get("places", [])) > 0
    assert "Good morning" not in d1b["response"]
    assert "Good afternoon" not in d1b["response"]
    print("  [PASS] 'mumbai' called search_places with Mumbai directly.")

    # -------------------------------------------------------------
    # CASE 1C (REGRESSION): Unmatched general message -> NO greeting fallback!
    # -------------------------------------------------------------
    print("\n[CASE 1C] Testing unmatched general question does not return welcome greeting...")
    res1c = client.post(
        "/ai/chat",
        headers={"Authorization": f"Bearer {t1_token}"},
        json={"message": "What should I pack for rain?", "conversation_id": f"conv_gen_{uuid.uuid4().hex[:6]}"}
    )
    assert res1c.status_code == 200
    d1c = res1c.json()
    assert d1c["tool_called"] is None
    assert "Good morning! 👋 I'm your TravelTrack AI Agent" not in d1c["response"]
    assert "Good afternoon! 👋 I'm your TravelTrack AI Agent" not in d1c["response"]
    assert "What should I pack for rain" in d1c["response"]
    print("  [PASS] General question acknowledged user input without falling back to initial welcome greeting.")

    # -------------------------------------------------------------
    # CASE 2: "hello" -> greeting only, ZERO tool calls
    # -------------------------------------------------------------
    print("\n[CASE 2] Testing 'hello' (pure greeting)...")
    res2 = client.post(
        "/ai/chat",
        headers={"Authorization": f"Bearer {t1_token}"},
        json={"message": "hello", "conversation_id": f"conv_c2_{uuid.uuid4().hex[:6]}"}
    )
    assert res2.status_code == 200
    d2 = res2.json()
    assert d2["tool_called"] is None, f"Expected tool_called=None, got '{d2['tool_called']}'"
    assert len(d2.get("places", [])) == 0
    assert "New Delhi" not in d2["response"]
    print("  [PASS] 'hello' returned natural greeting with ZERO tool calls.")

    # -------------------------------------------------------------
    # CASE 3: "thanks" -> normal response, ZERO tool calls
    # -------------------------------------------------------------
    print("\n[CASE 3] Testing 'thanks' (acknowledgment)...")
    res3 = client.post(
        "/ai/chat",
        headers={"Authorization": f"Bearer {t1_token}"},
        json={"message": "thanks", "conversation_id": f"conv_c3_{uuid.uuid4().hex[:6]}"}
    )
    assert res3.status_code == 200
    d3 = res3.json()
    assert d3["tool_called"] is None, f"Expected tool_called=None, got '{d3['tool_called']}'"
    assert len(d3.get("places", [])) == 0
    print("  [PASS] 'thanks' returned natural acknowledgment with ZERO tool calls.")

    # -------------------------------------------------------------
    # CASE 4: "what's my budget?" -> get_budget
    # -------------------------------------------------------------
    print("\n[CASE 4] Testing \"what's my budget?\"...")
    res4 = client.post(
        "/ai/chat",
        headers={"Authorization": f"Bearer {t1_token}"},
        json={"message": "what's my budget?", "trip_id": trip1_id, "conversation_id": conv_id}
    )
    assert res4.status_code == 200
    d4 = res4.json()
    assert d4["tool_called"] == "get_budget", f"Expected 'get_budget', got '{d4['tool_called']}'"
    assert "25,000" in d4["response"] or "17,000" in d4["response"]
    print(f"  [PASS] 'what's my budget?' called get_budget successfully.")

    # -------------------------------------------------------------
    # CASE 5: "what am I doing tomorrow?" -> get_itinerary
    # -------------------------------------------------------------
    print("\n[CASE 5] Testing 'what am I doing tomorrow?'...")
    res5 = client.post(
        "/ai/chat",
        headers={"Authorization": f"Bearer {t1_token}"},
        json={"message": "what am I doing tomorrow?", "trip_id": trip1_id, "conversation_id": conv_id}
    )
    assert res5.status_code == 200
    d5 = res5.json()
    assert d5["tool_called"] == "get_itinerary", f"Expected 'get_itinerary', got '{d5['tool_called']}'"
    print(f"  [PASS] 'what am I doing tomorrow?' called get_itinerary successfully.")

    # -------------------------------------------------------------
    # CASE 6: "find famous places in Kolkata" -> search_places for Kolkata
    # -------------------------------------------------------------
    kolkata_conv_id = f"conv_kolkata_{uuid.uuid4().hex[:6]}"
    print("\n[CASE 6] Testing 'find famous places in Kolkata'...")
    res6 = client.post(
        "/ai/chat",
        headers={"Authorization": f"Bearer {t1_token}"},
        json={"message": "find famous places in Kolkata", "conversation_id": kolkata_conv_id}
    )
    assert res6.status_code == 200
    d6 = res6.json()
    assert d6["tool_called"] == "search_places", f"Expected 'search_places', got '{d6['tool_called']}'"
    assert len(d6.get("places", [])) > 0, "Expected places for Kolkata"
    kolkata_first_place = d6["places"][0]["name"]
    print(f"  [PASS] 'find famous places in Kolkata' called search_places for Kolkata. Found: '{kolkata_first_place}'")

    # -------------------------------------------------------------
    # CASE 7: "find restaurants near Eiffel Tower" -> find_nearby_places
    # -------------------------------------------------------------
    print("\n[CASE 7] Testing 'find restaurants near Eiffel Tower'...")
    res7 = client.post(
        "/ai/chat",
        headers={"Authorization": f"Bearer {t1_token}"},
        json={"message": "find restaurants near Eiffel Tower", "conversation_id": f"conv_eiffel_{uuid.uuid4().hex[:6]}"}
    )
    assert res7.status_code == 200
    d7 = res7.json()
    assert d7["tool_called"] == "find_nearby_places", f"Expected 'find_nearby_places', got '{d7['tool_called']}'"
    print(f"  [PASS] 'find restaurants near Eiffel Tower' correctly routed to find_nearby_places.")

    # -------------------------------------------------------------
    # CASE 8: "add the first one to Day 3" -> add previous search result to Day 3
    # -------------------------------------------------------------
    print("\n[CASE 8] Testing follow-up 'add the first one to Day 3'...")
    res8 = client.post(
        "/ai/chat",
        headers={"Authorization": f"Bearer {t1_token}"},
        json={"message": "add the first one to Day 3", "trip_id": trip1_id, "conversation_id": kolkata_conv_id}
    )
    assert res8.status_code == 200
    d8 = res8.json()
    assert d8["tool_called"] == "add_itinerary_activity", f"Expected 'add_itinerary_activity', got '{d8['tool_called']}'"
    assert d8["mutation_occurred"] is True
    # Verify in MongoDB
    act = itineraries_collection.find_one({"trip_id": trip1_id, "day_number": 3})
    assert act is not None, "Activity was not written to MongoDB Day 3!"
    assert act["title"] == kolkata_first_place
    print(f"  [PASS] 'add the first one to Day 3' resolved '{kolkata_first_place}' from prior search and inserted into Day 3.")

    # -------------------------------------------------------------
    # CASE 9: "heyy" AFTER previously searching Kolkata -> STILL ONLY greeting!
    # -------------------------------------------------------------
    print("\n[CASE 9] Testing 'heyy' in same session after searching Kolkata...")
    res9 = client.post(
        "/ai/chat",
        headers={"Authorization": f"Bearer {t1_token}"},
        json={"message": "heyy", "conversation_id": kolkata_conv_id}
    )
    assert res9.status_code == 200
    d9 = res9.json()
    assert d9["tool_called"] is None, f"Expected tool_called=None, got '{d9['tool_called']}'"
    assert len(d9.get("places", [])) == 0, f"Expected 0 places, got {len(d9.get('places', []))}"
    print("  [PASS] 'heyy' after Kolkata search still responded as ONLY a greeting with ZERO tool calls!")

    # -------------------------------------------------------------
    # CASE 10: "find places" WITHOUT destination -> asks for destination, ZERO tool calls
    # -------------------------------------------------------------
    print("\n[CASE 10] Testing 'find places' with no destination...")
    res10 = client.post(
        "/ai/chat",
        headers={"Authorization": f"Bearer {t1_token}"},
        json={"message": "find places", "conversation_id": f"conv_generic_{uuid.uuid4().hex[:6]}"}
    )
    assert res10.status_code == 200
    d10 = res10.json()
    assert d10["tool_called"] is None, f"Expected tool_called=None, got '{d10['tool_called']}'"
    assert len(d10.get("places", [])) == 0
    assert "Which destination" in d10["response"]
    print("  [PASS] 'find places' without destination asked for city with ZERO tool calls.")

    # =============================================================
    # REMAINING SYSTEM & SECURITY TESTS
    # =============================================================

    # -------------------------------------------------------------
    # TEST 11: READ USER TRIPS
    # -------------------------------------------------------------
    print("\n[AI TEST 11] Asking AI to read my trips...")
    res11 = client.post(
        "/ai/chat",
        headers={"Authorization": f"Bearer {t1_token}"},
        json={"message": "Read my trips", "conversation_id": conv_id}
    )
    assert res11.status_code == 200
    d11 = res11.json()
    assert d11["tool_called"] == "get_user_trips"
    assert "Royal Hyderabad Odyssey" in d11["response"]
    print("  [PASS] AI read user trips correctly.")

    # -------------------------------------------------------------
    # TEST 12: DESTRUCTIVE ACTION CONFIRMATION STATE MACHINE
    # -------------------------------------------------------------
    print("\n[AI TEST 12] Testing Destructive Action Confirmation State Machine...")
    act_id = str(act["_id"])
    res_del_req = client.post(
        "/ai/chat",
        headers={"Authorization": f"Bearer {t1_token}"},
        json={"message": f"Delete activity {kolkata_first_place}", "trip_id": trip1_id, "conversation_id": conv_id}
    )
    assert res_del_req.status_code == 200
    del_data = res_del_req.json()
    assert del_data["requires_confirmation"] is True
    assert del_data["pending_action"] is not None
    assert del_data["pending_action"]["tool"] == "delete_itinerary_activity"
    print("  [PASS] AI requested confirmation before destructive action.")

    # Confirm deletion
    res_confirmed = client.post(
        "/ai/chat",
        headers={"Authorization": f"Bearer {t1_token}"},
        json={"message": "Yes, confirm", "trip_id": trip1_id, "conversation_id": conv_id, "confirm_action": True}
    )
    assert res_confirmed.status_code == 200
    conf_data = res_confirmed.json()
    assert conf_data["action_status"] == "executed"
    assert itineraries_collection.find_one({"_id": ObjectId(act_id)}) is None
    print("  [PASS] Verified deletion executed only AFTER explicit confirmation.")

    # -------------------------------------------------------------
    # TEST 13: MULTI-USER IDOR & DATA ISOLATION
    # -------------------------------------------------------------
    print("\n[AI TEST 13] Verifying Strict Multi-User Security & IDOR Isolation...")
    res_u2 = client.post(
        "/ai/chat",
        headers={"Authorization": f"Bearer {t2_token}"},
        json={"message": "How much budget do I have left?", "trip_id": trip1_id, "conversation_id": "u2_conv"}
    )
    assert res_u2.status_code == 200
    u2_data = res_u2.json()
    assert "Royal Hyderabad Odyssey" not in u2_data["response"]
    print("  [PASS] User 2 cannot access User 1's trip details.")

    # User 2 tries to delete User 1's trip
    res_u2_del = client.post(
        "/ai/chat",
        headers={"Authorization": f"Bearer {t2_token}"},
        json={"message": f"Delete trip {trip1_id}", "trip_id": trip1_id, "conversation_id": "u2_conv"}
    )
    assert res_u2_del.status_code == 200
    assert trips_collection.find_one({"_id": ObjectId(trip1_id)}) is not None
    print("  [PASS] User 2 cannot mutate User 1's trip.")

    # -------------------------------------------------------------
    # TEST 14: CONVERSATION HISTORY RETRIEVAL
    # -------------------------------------------------------------
    print("\n[AI TEST 14] Testing Conversation History Persistence...")
    hist_res = client.get(
        f"/ai/chat/history/{conv_id}",
        headers={"Authorization": f"Bearer {t1_token}"}
    )
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert len(hist_data.get("messages", [])) > 0
    print(f"  [PASS] Retrieved conversation history with {len(hist_data['messages'])} turns.")

    # Clean up test user data
    trips_collection.delete_many({"user_id": {"$in": [u1_id, u2_id]}})
    itineraries_collection.delete_many({"user_id": {"$in": [u1_id, u2_id]}})
    expenses_collection.delete_many({"user_id": {"$in": [u1_id, u2_id]}})
    wishlist_collection.delete_many({"user_id": {"$in": [u1_id, u2_id]}})
    chat_conversations_collection.delete_many({"user_id": {"$in": [u1_id, u2_id]}})

    print("\n" + "=" * 60)
    print("ALL AI TRAVEL AGENT TESTS (INCLUDING ALL 9 RULE CASES) PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    run_ai_agent_tests()
