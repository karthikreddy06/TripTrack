import json
import math
import os
import logging
import urllib.request
import urllib.error
from datetime import date, timedelta
from typing import List, Dict, Any, Optional, Set
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

logger = logging.getLogger("traveltrack.ai")

from app.auth import get_current_user
from app.database.mongodb import trips_collection, expenses_collection, wishlist_collection, chat_conversations_collection
from app.services.explore.provider import explore_provider
from app.services.ai_agent import ai_agent_service
from app.schemas.ai import (
    AITripPlanRequest,
    AITripPlanResponse,
    AIBudgetAdviceRequest,
    AIBudgetAdviceResponse,
    AIDayPlan,
    AITripActivity,
    AIChatRequest,
    AIChatResponse,
    ChatHistoryResponse,
    ChatMessageItem
)

router = APIRouter(
    prefix="/ai",
    tags=["AI Planner & Budget Assistant"]
)


def _haversine_distance(lat1: Optional[float], lon1: Optional[float], lat2: Optional[float], lon2: Optional[float]) -> float:
    """Calculate Great-Circle distance in km between two coordinate points."""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 0.0
    r = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2.0) ** 2 +
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def _generate_strict_unique_grounded_itinerary(
    dest: str,
    days: int,
    travelers: int,
    style: str,
    interests: List[str],
    budget: Optional[float],
    start_date_str: Optional[str],
    available_places: List[Dict[str, Any]],
    anchor_place_name: Optional[str] = None
) -> AITripPlanResponse:
    """
    Constructs an authentic day-by-day travel plan where every place and activity is strictly unique.
    - Never duplicates a place across days.
    - Groups geographically proximate places on the same day.
    - When all places are exhausted, schedules distinct lighter leisure & neighborhood discovery days.
    """
    days = max(1, min(days, 30))
    travelers = max(1, travelers)
    interests = interests or ["Culture & Heritage", "Local Cuisine & Food"]
    base_cost_per_day = 90.0 if not budget else (budget / days / travelers)

    # 1. Deduplicate available pool by canonical name
    pool: List[Dict[str, Any]] = []
    seen_canonical: Set[str] = set()
    for p in available_places:
        c_name = p.get("name", "").strip().lower()
        if c_name and c_name not in seen_canonical:
            seen_canonical.add(c_name)
            pool.append(p)

    # If anchor place is specified, move it to the front
    if anchor_place_name:
        norm_anchor = anchor_place_name.strip().lower()
        anchor_match = next((p for p in pool if norm_anchor in p.get("name", "").lower()), None)
        if anchor_match:
            pool.remove(anchor_match)
            pool.insert(0, anchor_match)

    # 2. Date calculation
    start_d = None
    if start_date_str:
        try:
            start_d = date.fromisoformat(start_date_str)
        except Exception:
            pass

    # 3. Global usage tracking (GUARANTEES 0 DUPLICATES ACROSS THE WHOLE TRIP)
    used_place_names: Set[str] = set()
    used_place_ids: Set[str] = set()
    used_activity_titles: Set[str] = set()

    day_plans: List[AIDayPlan] = []

    # Free day themes templates for days when real landmarks are exhausted
    free_day_templates = [
        (
            "Artisan Markets & Heritage Craft Trails",
            "Day focuses on traditional bazaars, handloom weavers, and local spice markets at a relaxed pace without repeating visited sights.",
            [
                ("10:00 AM", f"Morning Artisan Bazaars & Craft Stalls in {dest}", f"Central {dest} Bazaars", f"Explore vibrant market lanes, local handlooms, and traditional craft workshops in {dest}.", "activity", 0.25),
                ("01:00 PM", f"Historic Quarter Food Trail & Regional Lunch", f"Old Quarter, {dest}", f"Savor regional street delicacies and heritage family recipes in {dest}'s historic neighborhood.", "restaurant", 0.35),
                ("04:00 PM", f"Antique Shops & Cultural Courtyards Walk", f"{dest} Heritage District", f"Browse curated antique boutiques and relax in tranquil architectural courtyards.", "activity", 0.20),
                ("07:30 PM", f"Sunset Tea House & Evening Ambient Dining", f"{dest} Promenade", f"Unwind at an authentic local tea house with traditional sweets and evening breezes.", "restaurant", 0.20)
            ]
        ),
        (
            "Culinary Immersion & Local Neighborhood Living",
            "Day dedicated to culinary discoveries, neighborhood coffee culture, and observing daily life without crowded monuments.",
            [
                ("09:30 AM", f"Slow Morning: Specialty Coffee & Heritage Bakery Trail", f"Local Quarter, {dest}", f"Start with traditional breakfast specialties and artisanal baked goods at iconic neighborhood cafes.", "cafe", 0.20),
                ("01:00 PM", f"Chef-Curated Regional Tasting Session", f"{dest} Gourmet Quarter", f"Enjoy an immersive multi-course tasting session of signature regional dishes.", "restaurant", 0.40),
                ("04:30 PM", f"Neighborhood Garden & Tree-Lined Promenade Stroll", f"Greenway District, {dest}", f"Walk through scenic city gardens and community parks away from major traffic corridors.", "park", 0.15),
                ("08:00 PM", f"Open-Air Terrace Dinner & Night Ambiance", f"{dest} Skyline Terrace", f"Dine under the evening sky overlooking the illuminated city skyline.", "restaurant", 0.25)
            ]
        ),
        (
            "Scenic Waterfront & Golden Hour Photography",
            "Day designed for panoramic views, open landscapes, and golden hour light across scenic viewpoints.",
            [
                ("10:30 AM", f"Scenic Viewpoint & Panoramic Overlook Leisure", f"{dest} Heights", f"Take in sweeping panoramic perspectives across the historic and modern districts of {dest}.", "park", 0.20),
                ("01:30 PM", f"Waterfront Bistro Lunch & Refreshing Beverages", f"{dest} Waterfront", f"Enjoy fresh seasonal ingredients and chilled drinks with scenic water views.", "restaurant", 0.30),
                ("05:00 PM", f"Golden Hour Photography Trail & Open Plazas", f"{dest} Riverbanks", f"Capture striking architectural silhouettes and open horizons during the golden hour sunset.", "activity", 0.20),
                ("07:45 PM", f"Candlelit Evening Supper & Local Music Experience", f"Cultural Enclave, {dest}", f"Immerse yourself in acoustic regional music and relaxed evening hospitality.", "restaurant", 0.30)
            ]
        ),
        (
            "Relaxation, Wellness & Independent Exploration",
            "A restorative lighter day allowing personal discovery, bookshops, and unhurried city wandering.",
            [
                ("10:30 AM", f"Tranquil Morning: Botanical Greens & Independent Bookshops", f"{dest} Cultural Square", f"Recharge with a quiet morning exploring independent bookstores, art spaces, and serene botanical corners.", "park", 0.15),
                ("01:30 PM", f"Farm-to-Table Seasonal Lunch", f"Organic District, {dest}", f"Enjoy wholesome seasonal dishes made with locally sourced organic produce.", "restaurant", 0.35),
                ("04:00 PM", f"Open-Air Sculpture Walks & Creative Studios", f"Arts Enclave, {dest}", f"Discover contemporary public sculptures and local artist studio galleries at your own pace.", "museum", 0.20),
                ("07:30 PM", f"Relaxed Evening Gathering & Artisanal Dessert Tasting", f"{dest} Dessert Alley", f"Sample handcrafted sweets and regional dessert specialties to conclude the day.", "cafe", 0.30)
            ]
        ),
        (
            "Grand Farewell & Journey Celebration",
            "Final celebratory day dedicated to souvenir shopping, revisiting favorite neighborhood vibes, and a grand concluding dinner.",
            [
                ("10:30 AM", f"Curated Souvenir & Gift Discovery Trail", f"{dest} Artisan Guilds", f"Select handcrafted mementos, spices, textiles, and authentic regional keepsakes.", "activity", 0.25),
                ("01:30 PM", f"Farewell Feast of Regional Favorites", f"{dest} Culinary Center", f"Celebrate your trip with a memorable feast featuring your favorite culinary discoveries.", "restaurant", 0.40),
                ("05:00 PM", f"Twilight Sunset Reflection & City Panorama", f"{dest} Grand Overlook", f"Reflect on your travel journey with majestic twilight views over the city.", "park", 0.10),
                ("08:00 PM", f"Grand Finale Gala Dinner in Historic {dest}", f"{dest} Grand Hall", f"A celebratory final dinner commemorating a seamless, beautifully curated exploration.", "restaurant", 0.25)
            ]
        )
    ]

    free_day_idx = 0

    for d in range(1, days + 1):
        day_date_str = ""
        if start_d:
            current_date = start_d + timedelta(days=d - 1)
            day_date_str = current_date.isoformat()

        # Find unvisited places from the pool
        unvisited = [
            p for p in pool
            if p.get("name", "").strip().lower() not in used_place_names
            and (p.get("id") or p.get("place_id") or "") not in used_place_ids
        ]

        day_activities: List[AITripActivity] = []

        if len(unvisited) > 0:
            # Pick seed place for this day
            lead_place = unvisited[0]
            lead_name = lead_place.get("name", "").strip()
            lead_id = lead_place.get("id") or lead_place.get("place_id") or ""
            lead_lat = lead_place.get("lat")
            lead_lon = lead_place.get("lon")

            used_place_names.add(lead_name.lower())
            if lead_id:
                used_place_ids.add(lead_id)

            # Activity 1: Morning exploration of lead place
            act1_title = lead_name
            used_activity_titles.add(act1_title.lower())
            day_activities.append(
                AITripActivity(
                    time="09:30 AM",
                    title=act1_title,
                    location=lead_place.get("address") or lead_place.get("location") or f"{dest}",
                    description=lead_place.get("description") or f"Explore {lead_name} in {dest}.",
                    place_id=lead_id or None,
                    category=lead_place.get("category", "attraction"),
                    lat=lead_lat,
                    lon=lead_lon,
                    distance_km=0.0,
                    estimated_cost=round(base_cost_per_day * 0.25, 2)
                )
            )

            # Find closest unvisited places to lead_place
            remaining_unvisited = [
                p for p in pool
                if p.get("name", "").strip().lower() not in used_place_names
                and (p.get("id") or p.get("place_id") or "") not in used_place_ids
            ]

            # Sort by distance from lead_place
            remaining_unvisited.sort(
                key=lambda p: _haversine_distance(lead_lat, lead_lon, p.get("lat"), p.get("lon"))
            )

            # Activity 2 (01:00 PM) - Lunch or closest dining / sightseeing
            if len(remaining_unvisited) > 0:
                p2 = remaining_unvisited[0]
                p2_name = p2.get("name", "").strip()
                p2_id = p2.get("id") or p2.get("place_id") or ""
                p2_lat = p2.get("lat")
                p2_lon = p2.get("lon")
                dist2 = round(_haversine_distance(lead_lat, lead_lon, p2_lat, p2_lon), 1)

                used_place_names.add(p2_name.lower())
                if p2_id:
                    used_place_ids.add(p2_id)
                used_activity_titles.add(p2_name.lower())

                day_activities.append(
                    AITripActivity(
                        time="01:00 PM",
                        title=p2_name,
                        location=p2.get("address") or p2.get("location") or f"{dest}",
                        description=p2.get("description") or f"Discover {p2_name} located {dist2} km from {lead_name}.",
                        place_id=p2_id or None,
                        category=p2.get("category", "restaurant"),
                        lat=p2_lat,
                        lon=p2_lon,
                        distance_km=dist2,
                        estimated_cost=round(base_cost_per_day * 0.35, 2)
                    )
                )
                remaining_unvisited.pop(0)
            else:
                act2_title = f"Authentic Midday Dining in {lead_name} District"
                used_activity_titles.add(act2_title.lower())
                day_activities.append(
                    AITripActivity(
                        time="01:00 PM",
                        title=act2_title,
                        location=lead_place.get("address") or f"{dest}",
                        description=f"Enjoy regional gastronomy and culinary specialties in the surrounding quarter of {lead_name}.",
                        place_id=None,
                        category="restaurant",
                        lat=lead_lat,
                        lon=lead_lon,
                        distance_km=0.3,
                        estimated_cost=round(base_cost_per_day * 0.35, 2)
                    )
                )

            # Activity 3 (03:30 PM) - Afternoon attraction or cultural exploration
            if len(remaining_unvisited) > 0:
                p3 = remaining_unvisited[0]
                p3_name = p3.get("name", "").strip()
                p3_id = p3.get("id") or p3.get("place_id") or ""
                p3_lat = p3.get("lat")
                p3_lon = p3.get("lon")
                dist3 = round(_haversine_distance(lead_lat, lead_lon, p3_lat, p3_lon), 1)

                used_place_names.add(p3_name.lower())
                if p3_id:
                    used_place_ids.add(p3_id)
                used_activity_titles.add(p3_name.lower())

                day_activities.append(
                    AITripActivity(
                        time="03:30 PM",
                        title=p3_name,
                        location=p3.get("address") or p3.get("location") or f"{dest}",
                        description=p3.get("description") or f"Explore {p3_name} in the afternoon ({dist3} km from {lead_name}).",
                        place_id=p3_id or None,
                        category=p3.get("category", "museum"),
                        lat=p3_lat,
                        lon=p3_lon,
                        distance_km=dist3,
                        estimated_cost=round(base_cost_per_day * 0.20, 2)
                    )
                )
                remaining_unvisited.pop(0)
            else:
                act3_title = f"Afternoon Cultural Stroll & Crafts near {lead_name}"
                used_activity_titles.add(act3_title.lower())
                day_activities.append(
                    AITripActivity(
                        time="03:30 PM",
                        title=act3_title,
                        location=lead_place.get("address") or f"{dest}",
                        description=f"Browse artisanal craft boutiques, street markets, and architectural lanes in the vicinity of {lead_name}.",
                        place_id=None,
                        category="activity",
                        lat=lead_lat,
                        lon=lead_lon,
                        distance_km=0.5,
                        estimated_cost=round(base_cost_per_day * 0.20, 2)
                    )
                )

            # Activity 4 (07:00 PM) - Evening ambience / dining
            act4_title = f"Sunset Promenade & Evening Ambience around {lead_name}"
            used_activity_titles.add(act4_title.lower())
            day_activities.append(
                AITripActivity(
                    time="07:00 PM",
                    title=act4_title,
                    location=lead_place.get("address") or f"{dest}",
                    description=f"Unwind with scenic evening lighting, relaxed walking paths, and local desserts near {lead_name}.",
                    place_id=None,
                    category="park",
                    lat=lead_lat,
                    lon=lead_lon,
                    distance_km=0.8,
                    estimated_cost=round(base_cost_per_day * 0.20, 2)
                )
            )

            theme = f"{lead_name} & Neighboring District"
            rationale = (
                f"Day {d} is optimized around {lead_name}, grouping geographically proximate "
                f"sights within close proximity to minimize cross-city transit."
            )

        else:
            # NO PLACES LEFT IN POOL -> Create a dedicated lighter/free day without duplicating ANY place!
            template = free_day_templates[free_day_idx % len(free_day_templates)]
            free_day_idx += 1
            theme = template[0]
            rationale = template[1]

            for time_val, act_title, act_loc, act_desc, act_cat, cost_factor in template[2]:
                unique_title = act_title
                # Ensure title has not been used
                if unique_title.lower() in used_activity_titles:
                    unique_title = f"Day {d}: {unique_title}"
                used_activity_titles.add(unique_title.lower())

                day_activities.append(
                    AITripActivity(
                        time=time_val,
                        title=unique_title,
                        location=act_loc,
                        description=act_desc,
                        place_id=None,
                        category=act_cat,
                        lat=None,
                        lon=None,
                        distance_km=None,
                        estimated_cost=round(base_cost_per_day * cost_factor, 2)
                    )
                )

        day_plans.append(
            AIDayPlan(
                day=d,
                date=day_date_str,
                theme=theme,
                rationale=rationale,
                activities=day_activities
            )
        )

    # 4. Global Packing List & Travel Tips
    packing_list = [
        "Government ID / Passport & digital confirmation documents",
        "Universal power adapter and high-capacity portable power bank",
        "Comfortable cushioned walking shoes for city explorations",
        "Light breathable layers and compact water-resistant jacket",
        "Reusable insulated water bottle & personal sun protection (SPF 50+)",
        "Local currency cash reserve for street markets, tea stalls & transit"
    ]
    if any(k in interests for k in ["Beaches & Coastal", "Nature & Landscapes"]):
        packing_list.append("Reef-safe sunscreen, quick-dry microfibre towel & polarized sunglasses")
    if any(k in interests for k in ["Adventure & Hiking", "Photography"]):
        packing_list.append("Sturdy trail footwear, compact daypack & camera equipment")

    travel_tips = [
        f"Every day's itinerary is strictly non-repeating and clustered geographically to reduce transit times.",
        f"Early mornings (before 10:30 AM) offer the calmest lighting and lowest crowds at major landmarks in {dest}.",
        f"Consider local transit passes or rideshare for seamless transfers between daily geographic clusters.",
        f"Reserve priority dining and specialty tasting sessions 24 hours in advance.",
        f"Keep offline maps downloaded for effortless navigation without mobile roaming data."
    ]

    total_est_budget = budget if budget else (days * 140.0 * travelers)
    budget_breakdown = {
        "Accommodation": round(total_est_budget * 0.40, 2),
        "Food": round(total_est_budget * 0.25, 2),
        "Activities": round(total_est_budget * 0.18, 2),
        "Transport": round(total_est_budget * 0.12, 2),
        "Other": round(total_est_budget * 0.05, 2)
    }

    anchor_note = f" centered around {anchor_place_name}" if anchor_place_name else ""
    summary = (
        f"A strictly non-repeating, data-grounded {days}-day itinerary for {travelers} traveler{'s' if travelers > 1 else ''} in {dest}{anchor_note}, "
        f"optimized geographically with {len(used_place_names)} unique landmarks and tailored pacing."
    )

    itinerary_rationale = (
        f"This itinerary organizes {dest}'s top verified landmarks into geographically proximate clusters without repeating any place. "
        f"Daily schedules group morning heritage sights, afternoon culture, and evening dining within tight travel radii, "
        f"transitioning into immersive leisure and neighborhood discovery on extended days."
    )

    return AITripPlanResponse(
        destination=dest,
        days=days,
        summary=summary,
        itinerary_rationale=itinerary_rationale,
        itinerary=day_plans,
        packing_list=packing_list,
        travel_tips=travel_tips,
        budget_breakdown=budget_breakdown,
        source="data_driven_cluster"
    )


@router.post("/plan-trip", status_code=status.HTTP_200_OK, response_model=AITripPlanResponse)
async def plan_trip_with_ai(
    req: AITripPlanRequest,
    current_user_id: str = Depends(get_current_user)
):
    """
    Generate an AI-powered travel itinerary grounded in real OpenStreetMap TravelTrack data.
    Enforces STRICT place uniqueness — NO place repeats across days.
    """
    dest = req.destination.strip().title()

    # 1. Fetch real Explore places for this destination
    search_res = await explore_provider.search_places(query=dest, category="all", page=1, limit=60)
    real_places = search_res.get("places", [])

    # 2. Fetch user's wishlist places for this destination if enabled
    wishlist_places = []
    if req.include_wishlist and current_user_id:
        try:
            wl_cursor = wishlist_collection.find({"user_id": current_user_id})
            for item in wl_cursor:
                loc = item.get("location", "")
                if dest.lower() in loc.lower() or dest.lower() in item.get("name", "").lower():
                    meta = item.get("metadata", {})
                    wishlist_places.append({
                        "id": item.get("place_id", str(item.get("_id"))),
                        "place_id": item.get("place_id"),
                        "name": item.get("name"),
                        "category": item.get("category", "attraction"),
                        "address": loc,
                        "description": item.get("description", ""),
                        "lat": meta.get("lat"),
                        "lon": meta.get("lon")
                    })
        except Exception:
            pass

    # Merge wishlist places first, then explore places
    all_available = list(wishlist_places)
    seen_ids = set(p["id"] for p in all_available)
    for p in real_places:
        p_id = p.get("id") or p.get("place_id")
        if p_id not in seen_ids:
            all_available.append(p)
            seen_ids.add(p_id)

    # 3. Generate strictly unique grounded itinerary
    return _generate_strict_unique_grounded_itinerary(
        dest=dest,
        days=req.days,
        travelers=req.travelers,
        style=req.travel_style or "Balanced",
        interests=req.interests,
        budget=req.budget,
        start_date_str=req.start_date,
        available_places=all_available,
        anchor_place_name=req.anchor_place_name
    )


@router.post("/budget-advice", status_code=status.HTTP_200_OK, response_model=AIBudgetAdviceResponse)
def get_budget_advice(
    req: AIBudgetAdviceRequest,
    current_user_id: str = Depends(get_current_user)
):
    """
    AI Budget Assistant analyzing trip budget vs real expenses and suggesting cost-saving actions.
    """
    if not ObjectId.is_valid(req.trip_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid trip ID format"
        )

    try:
        trip = trips_collection.find_one({"_id": ObjectId(req.trip_id), "user_id": current_user_id})
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database query error: {str(exc)}"
        )

    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )

    budget = float(trip.get("budget", 0.0))
    destination = trip.get("destination", "Destination")

    try:
        expenses = list(expenses_collection.find({"trip_id": req.trip_id}))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database query error: {str(exc)}"
        )

    total_spent = sum(float(e.get("amount", 0.0)) for e in expenses)
    remaining = budget - total_spent
    pct_spent = (total_spent / budget * 100) if budget > 0 else 0.0

    by_cat = {}
    for e in expenses:
        c = e.get("category", "Other")
        by_cat[c] = by_cat.get(c, 0.0) + float(e.get("amount", 0.0))

    highest_cat = max(by_cat, key=by_cat.get) if by_cat else "Accommodation"

    if budget <= 0:
        status_code = "caution"
        summary = f"No fixed budget set for your {destination} journey."
        analysis = f"You have recorded {len(expenses)} expense(s) totaling ${total_spent:.2f}. Set a target budget to unlock full financial tracking."
        saving_tips = [
            "Set a baseline trip budget in Trip Settings.",
            "Log expenses daily to catch incidental overspending early."
        ]
    elif pct_spent > 100:
        status_code = "overbudget"
        over_amt = total_spent - budget
        summary = f"You are currently ${over_amt:.2f} over your ${budget:.2f} budget ({pct_spent:.1f}% spent)."
        analysis = f"Heavy spending in {highest_cat} (${by_cat.get(highest_cat, 0):.2f}) is driving budget overruns."
        saving_tips = [
            f"Review pending activities in {highest_cat} for budget-friendly alternatives.",
            "Consider public transit or walking passes instead of private taxis.",
            "Opt for local neighborhood dining for subsequent meals."
        ]
    elif pct_spent >= 80:
        status_code = "caution"
        summary = f"You have utilized {pct_spent:.1f}% of your budget (${remaining:.2f} remaining)."
        analysis = f"Spending is nearing your budget limit. {highest_cat} represents your largest expenditure."
        saving_tips = [
            "Prioritize free museum days and public park walks.",
            "Limit high-tier dining to celebrate the final evening."
        ]
    else:
        status_code = "on_track"
        summary = f"Your finances are well-managed at {pct_spent:.1f}% spent (${remaining:.2f} available)."
        analysis = f"Healthy budget allocation across {len(expenses)} logged expense(s)."
        saving_tips = [
            "Keep maintaining your balanced daily spending pace.",
            "Consider allocating a small reserve for spontaneous cultural events."
        ]

    category_allocations = {
        "Accommodation": f"{round(by_cat.get('Accommodation', 0) / (total_spent or 1) * 100, 1)}%",
        "Food": f"{round(by_cat.get('Food', 0) / (total_spent or 1) * 100, 1)}%",
        "Transport": f"{round(by_cat.get('Transport', 0) / (total_spent or 1) * 100, 1)}%",
        "Activities": f"{round(by_cat.get('Activities', 0) / (total_spent or 1) * 100, 1)}%",
        "Other": f"{round(by_cat.get('Other', 0) / (total_spent or 1) * 100, 1)}%"
    }

    return AIBudgetAdviceResponse(
        trip_id=req.trip_id,
        status=status_code,
        summary=summary,
        analysis=analysis,
        saving_tips=saving_tips,
        category_allocations=category_allocations
    )


# =====================================================================
# REAL CONTEXT-AWARE AI TRAVEL AGENT CHAT ENDPOINTS
# =====================================================================

@router.post("/chat", response_model=AIChatResponse, status_code=status.HTTP_200_OK)
async def chat_with_agent(
    req: AIChatRequest,
    current_user_id: str = Depends(get_current_user)
):
    """
    Interact with the context-aware AI travel agent.
    Performs dynamic tool calling, reads/writes real TravelTrack user data,
    resolves conversational references, and manages confirmations for destructive actions.
    """
    try:
        # Development logging: inspect input state & history
        conv_doc = chat_conversations_collection.find_one({
            "user_id": current_user_id,
            "conversation_id": req.conversation_id
        })
        history_count = len(conv_doc.get("messages", [])) if conv_doc else 0

        logger.info(
            f"[AI_CHAT_IN] user_id={current_user_id[:6]}... | "
            f"conv_id='{req.conversation_id}' | "
            f"history_msgs={history_count} | "
            f"msg='{req.message}'"
        )

        result = await ai_agent_service.process_chat(
            user_id=current_user_id,
            message=req.message,
            explicit_trip_id=req.trip_id,
            conversation_id=req.conversation_id,
            confirm_action=req.confirm_action
        )

        logger.info(
            f"[AI_CHAT_OUT] conv_id='{req.conversation_id}' | "
            f"tool_called='{result.get('tool_called')}' | "
            f"places_count={len(result.get('places', []))} | "
            f"response_snippet='{result.get('response', '')[:100]}...'"
        )

        return AIChatResponse(**result)
    except Exception as exc:
        logger.error(f"Error in chat_with_agent: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The AI Travel Agent encountered an issue processing your request. Please try again."
        )


@router.get("/chat/history/{conversation_id}", response_model=ChatHistoryResponse, status_code=status.HTTP_200_OK)
def get_chat_history(
    conversation_id: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    Retrieve stored conversation history for the authenticated user and conversation.
    """
    doc = chat_conversations_collection.find_one({
        "user_id": current_user_id,
        "conversation_id": conversation_id
    })
    if not doc:
        return ChatHistoryResponse(conversation_id=conversation_id, messages=[])

    raw_msgs = doc.get("messages", [])
    valid_msgs = []
    for m in raw_msgs:
        valid_msgs.append(ChatMessageItem(
            id=m.get("id", "msg"),
            role=m.get("role", "user"),
            content=m.get("content", ""),
            timestamp=m.get("timestamp", ""),
            tool_called=m.get("tool_called"),
            tool_result=m.get("tool_result"),
            action_status=m.get("action_status"),
            pending_action=m.get("pending_action"),
            places=m.get("places")
        ))

    return ChatHistoryResponse(conversation_id=conversation_id, messages=valid_msgs)


@router.delete("/chat/history/{conversation_id}", status_code=status.HTTP_200_OK)
def clear_chat_history(
    conversation_id: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    Clear a conversation history session for the authenticated user.
    """
    chat_conversations_collection.delete_one({
        "user_id": current_user_id,
        "conversation_id": conversation_id
    })
    return {"message": "Chat session cleared successfully."}

