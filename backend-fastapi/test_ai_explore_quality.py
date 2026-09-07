import asyncio
import sys
import os

# Set UTF-8 for stdout
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath("backend-fastapi"))

from app.services.explore.provider import explore_provider
from app.services.explore.overpass import EXCLUDED_NAME_REGEX, EXCLUDED_AMENITIES
from app.services.ai_agent import ai_agent_service

async def test_explore_quality():
    print("\n" + "=" * 60)
    print("1. TESTING EXPLORE MULTI-SIGNAL PLACE RANKING & NOISE FILTERING")
    print("=" * 60)

    cities_to_test = ["Mumbai", "Delhi", "Paris", "Tokyo", "Kolkata", "Kyoto"]
    
    for city in cities_to_test:
        print(f"\n--- Testing City: {city} ---")
        res = await explore_provider.search_places(query=city, category="all", limit=8)
        places = res.get("places", [])
        print(f"Total verified places returned: {len(places)}")
        
        assert len(places) > 0, f"Expected places for {city}, got 0"
        
        for idx, p in enumerate(places, 1):
            name = p.get("name")
            cat = p.get("category")
            score = p.get("travel_score", 0)
            print(f"  {idx}. {name} | Category: {cat} | Travel Score: {score:.1f}")
            
            # Verify no noise keywords in name
            assert not EXCLUDED_NAME_REGEX.search(name) or (p.get("osm_wikipedia") or p.get("osm_wikidata")), f"FAIL: Noise entity found in {city}: {name}"
            
            # Verify category is valid travel category
            assert cat in ["attraction", "historic", "museum", "park", "activity", "hotel", "restaurant", "cafe"], f"Invalid category: {cat}"

    print("\n[PASSED] Explore Quality & Noise Filtering Tests Passed for all cities!")


async def test_ai_agent_general_qa():
    print("\n" + "=" * 60)
    print("2. TESTING AI AGENT GENERAL KNOWLEDGE (NO TOOLS / NO COMMAND BOT)")
    print("=" * 60)

    test_queries = [
        "What is Python?",
        "Explain recursion",
        "Explain quantum computing",
        "Write a FastAPI example",
        "Tell me a joke",
        "Why is my code slow?",
        "What is machine learning?"
    ]

    mock_user_id = "test_user_ai_quality"
    
    for q in test_queries:
        print(f"\nUser: \"{q}\"")
        res = await ai_agent_service.process_chat(
            user_id=mock_user_id,
            message=q,
            conversation_id="conv_general_test"
        )
        response_text = res.get("response", "")
        tool_called = res.get("tool_called")
        
        print(f"AI: {response_text[:140]}...")
        
        # General QA must NOT call travel tools
        assert tool_called is None, f"FAIL: General query '{q}' triggered tool '{tool_called}'"
        
        # Must not contain command bot strings
        assert "Supported commands are" not in response_text
        assert "I received your message" not in response_text
        assert len(response_text) > 40, f"Response too short for query '{q}'"

    print("\n[PASSED] AI Agent General Knowledge Tests Passed!")


async def test_ai_travel_context_flow():
    print("\n" + "=" * 60)
    print("3. TESTING AI AGENT TRAVEL RECOMMENDATIONS & MULTI-TURN CONVERSATION")
    print("=" * 60)

    mock_user_id = "test_user_travel_flow"
    conv_id = f"conv_flow_{int(time.time() * 1000)}"

    # Step 1: User asks for places in Kyoto
    q1 = "What should I visit in Kyoto?"
    print(f"\nUser Turn 1: \"{q1}\"")
    res1 = await ai_agent_service.process_chat(user_id=mock_user_id, message=q1, conversation_id=conv_id)
    print(f"Tool: {res1.get('tool_called')}")
    print(f"AI Response:\n{res1.get('response')[:250]}...")
    assert res1.get("tool_called") == "search_places"
    assert len(res1.get("places", [])) > 0

    # Step 2: Contextual follow-up ("Which one is best for history?")
    q2 = "Which one is best for history?"
    print(f"\nUser Turn 2: \"{q2}\"")
    res2 = await ai_agent_service.process_chat(user_id=mock_user_id, message=q2, conversation_id=conv_id)
    print(f"AI Response:\n{res2.get('response')}")
    assert res2.get("tool_called") is None
    assert "History" in res2.get("response") or "historic" in res2.get("response").lower()

    # Step 3: Add to wishlist
    q3 = "Save the first one to my wishlist"
    print(f"\nUser Turn 3: \"{q3}\"")
    res3 = await ai_agent_service.process_chat(user_id=mock_user_id, message=q3, conversation_id=conv_id)
    print(f"Tool: {res3.get('tool_called')}")
    print(f"AI Response: {res3.get('response')}")
    assert res3.get("tool_called") == "add_wishlist"

    print("\n[PASSED] Multi-turn AI Travel Context Flow Tests Passed!")


async def main():
    await test_explore_quality()
    await test_ai_agent_general_qa()
    await test_ai_travel_context_flow()
    print("\n" + "=" * 60)
    print("ALL TEST SUITES PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    import time
    asyncio.run(main())
