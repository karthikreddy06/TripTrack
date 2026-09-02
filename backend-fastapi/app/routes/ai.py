import json
import os
import urllib.request
import urllib.error
from datetime import date, timedelta
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_user
from app.database.mongodb import trips_collection, expenses_collection
from app.schemas.ai import (
    AITripPlanRequest,
    AITripPlanResponse,
    AIBudgetAdviceRequest,
    AIBudgetAdviceResponse,
    AIDayPlan,
    AITripActivity
)

router = APIRouter(
    prefix="/ai",
    tags=["AI Planner & Budget Assistant"]
)


def _generate_fallback_itinerary(req: AITripPlanRequest) -> AITripPlanResponse:
    """
    Generates a rich, structured, dynamic itinerary when no external AI API key is configured.
    Tailors recommendations to destination, travel style, interests, and duration.
    """
    dest = req.destination.strip().title()
    days = max(1, min(req.days, 30))
    travelers = req.travelers
    style = req.travel_style or "Balanced"
    interests = req.interests or ["Sightseeing", "Local Cuisine", "Culture"]

    # Calculate dates if start_date provided
    start_d = None
    if req.start_date:
        try:
            start_d = date.fromisoformat(req.start_date)
        except Exception:
            pass

    time_slots = [
        ("09:00 AM", "Morning Discovery & Landmarks", f"Explore iconic heritage sites and scenic morning viewpoints around central {dest}."),
        ("12:30 PM", "Authentic Local Dining", f"Savor signature culinary specialties and regional delicacies curated for {style.lower()} travelers."),
        ("03:30 PM", "Immersive Experience & Culture", f"Engage in {', '.join(interests[:2]) if interests else 'cultural exploration'} and neighborhood exploration in {dest}."),
        ("07:30 PM", "Evening Ambience & Relaxation", f"Unwind at a scenic sunset terrace or lively district capturing the true atmosphere of {dest}.")
    ]

    day_plans = []
    base_cost_per_day = 80.0 if not req.budget else (req.budget / days / max(travelers, 1))

    for day_num in range(1, days + 1):
        day_date_str = ""
        if start_d:
            current_date = start_d + timedelta(days=day_num - 1)
            day_date_str = current_date.isoformat()

        activities = []
        for time_val, title_template, desc in time_slots:
            cost_factor = 0.25 if "Dining" in title_template else (0.4 if "Morning" in title_template else 0.2)
            act_cost = round(base_cost_per_day * cost_factor, 2)

            activities.append(
                AITripActivity(
                    time=time_val,
                    title=f"Day {day_num} — {title_template}",
                    location=f"{dest} District {day_num}",
                    description=desc,
                    estimated_cost=act_cost
                )
            )

        theme_titles = [
            f"Arrival & Central {dest} Highlights",
            f"Heritage, Architecture & Hidden Gems",
            f"Culinary Tastings & Artisan Markets",
            f"Nature, Scenic Panoramas & Relaxation",
            f"Local Neighbourhoods & Art Scene",
            f"Excursions & Outdoor Adventure",
            f"Souvenirs, Grand Finale & Sunset Views"
        ]
        theme = theme_titles[(day_num - 1) % len(theme_titles)]

        day_plans.append(
            AIDayPlan(
                day=day_num,
                date=day_date_str,
                theme=theme,
                activities=activities
            )
        )

    # Tailored packing list
    packing_list = [
        "Passport, visa documents & digital travel insurance copies",
        "Universal power adapter and portable power bank",
        "Comfortable walking shoes suitable for city explorations",
        "Lightweight weather-appropriate layering and rain jacket",
        "Reusable water bottle & compact personal first-aid pouch",
        "Offline map downloads and local currency cash reserve"
    ]
    if "Beaches" in interests:
        packing_list.append("Reef-safe sunscreen, swimwear & UV sunglasses")
    if "Adventure" in interests or "Nature" in interests:
        packing_list.append("Durable hiking footwear & compact daypack")

    # Smart travel tips
    travel_tips = [
        f"Pre-book priority access tickets for top {dest} attractions to bypass peak lines.",
        f"Public transit passes in {dest} offer substantial savings compared to single ride tickets.",
        f"Notify your bank before departure to prevent unexpected card locks abroad.",
        f"Keep digital offline copies of hotel reservations and emergency contacts.",
        f"Embrace local dining customs by eating during traditional regional meal hours."
    ]

    total_est_budget = req.budget if req.budget else (days * 150.0 * max(travelers, 1))
    budget_breakdown = {
        "Accommodation": round(total_est_budget * 0.40, 2),
        "Food": round(total_est_budget * 0.25, 2),
        "Activities": round(total_est_budget * 0.18, 2),
        "Transport": round(total_est_budget * 0.12, 2),
        "Other": round(total_est_budget * 0.05, 2)
    }

    return AITripPlanResponse(
        destination=dest,
        days=days,
        summary=f"A curated {days}-day {style.lower()} itinerary for {travelers} traveler{'s' if travelers > 1 else ''} in {dest} tailored around {', '.join(interests)}.",
        itinerary=day_plans,
        packing_list=packing_list,
        travel_tips=travel_tips,
        budget_breakdown=budget_breakdown,
        source="template_fallback"
    )


@router.post("/plan-trip", status_code=status.HTTP_200_OK, response_model=AITripPlanResponse)
def plan_trip_with_ai(
    req: AITripPlanRequest,
    current_user_id: str = Depends(get_current_user)
):
    """
    Generate an AI-powered structured travel itinerary.
    Uses GEMINI_API_KEY or OPENAI_API_KEY if present in environment variables.
    Falls back gracefully to intelligent dynamic generator if keys are unconfigured.
    """
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    prompt = (
        f"Generate a detailed {req.days}-day travel itinerary for {req.destination} for {req.travelers} traveler(s). "
        f"Travel style: {req.travel_style}. Interests: {', '.join(req.interests)}. "
        f"Budget: {req.budget or 'flexible'}. "
        "Return ONLY a valid JSON object matching this schema: "
        "{\n"
        '  "destination": string,\n'
        '  "days": number,\n'
        '  "summary": string,\n'
        '  "itinerary": [\n'
        '    {\n'
        '      "day": number,\n'
        '      "date": string,\n'
        '      "theme": string,\n'
        '      "activities": [\n'
        '        {\n'
        '          "time": string,\n'
        '          "title": string,\n'
        '          "location": string,\n'
        '          "description": string,\n'
        '          "estimated_cost": number\n'
        '        }\n'
        '      ]\n'
        '    }\n'
        '  ],\n'
        '  "packing_list": [string],\n'
        '  "travel_tips": [string],\n'
        '  "budget_breakdown": {\n'
        '    "Accommodation": number,\n'
        '    "Food": number,\n'
        '    "Transport": number,\n'
        '    "Activities": number,\n'
        '    "Other": number\n'
        '  }\n'
        "}"
    )

    # 1. Try Gemini API if key is configured
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key.strip()}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "response_mime_type": "application/json",
                    "temperature": 0.4
                }
            }
            req_data = json.dumps(payload).encode("utf-8")
            req_obj = urllib.request.Request(
                url,
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req_obj, timeout=12) as response:
                res_body = json.loads(response.read().decode("utf-8"))
                text_content = res_body["candidates"][0]["content"]["parts"][0]["text"]
                parsed_json = json.loads(text_content)
                parsed_json["source"] = "ai"
                return AITripPlanResponse(**parsed_json)
        except Exception:
            # On any API error, safely fall back without failing the user request
            pass

    # 2. Try OpenAI API if key is configured
    if openai_key:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            payload = {
                "model": "gpt-4o-mini",
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": "You are a professional travel curator. Output only JSON matching the schema."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.4
            }
            req_data = json.dumps(payload).encode("utf-8")
            req_obj = urllib.request.Request(
                url,
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {openai_key.strip()}"
                }
            )
            with urllib.request.urlopen(req_obj, timeout=12) as response:
                res_body = json.loads(response.read().decode("utf-8"))
                text_content = res_body["choices"][0]["message"]["content"]
                parsed_json = json.loads(text_content)
                parsed_json["source"] = "ai"
                return AITripPlanResponse(**parsed_json)
        except Exception:
            pass

    # 3. Default high-quality structured generator
    return _generate_fallback_itinerary(req)


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

    if budget == 0:
        status_code = "caution"
        summary = f"No budget cap configured for {destination}. Total logged expenses are ${total_spent:,.2f}."
        analysis = "Set a target budget cap to enable full financial health metrics and runway tracking."
        saving_tips = [
            "Establish a daily spending limit based on anticipated itinerary days.",
            "Group expenses by category to pinpoint unexpected outlays early."
        ]
    elif pct_spent > 100:
        status_code = "overbudget"
        over_amount = total_spent - budget
        summary = f"Budget exceeded by ${over_amount:,.2f} ({pct_spent:.1f}% spent)."
        analysis = f"Your highest expense category is {highest_cat} (${by_cat.get(highest_cat, 0):,.2f}). Immediate adjustments are recommended on remaining activities and dining."
        saving_tips = [
            f"Prioritize free or discounted local activities in {destination} for remainder of the journey.",
            "Swap full-service sit-down dinners for authentic local street eats and market dining.",
            "Review booking cancellations or refunds for non-essential tours."
        ]
    elif pct_spent >= 80:
        status_code = "caution"
        summary = f"Approaching budget limit: {pct_spent:.1f}% utilized (${remaining:,.2f} remaining)."
        analysis = f"You are on pace to exhaust your funds soon. {highest_cat} accounts for the largest proportion of expenditures."
        saving_tips = [
            f"Cap upcoming daily expenses to avoid crossing your target ceiling of ${budget:,.2f}.",
            "Use public transit and regional rail passes instead of on-demand taxi rides.",
            "Look for lunch specials at popular dining venues which often cost 30-50% less than evening menus."
        ]
    else:
        status_code = "on_track"
        summary = f"Healthy budget state: {pct_spent:.1f}% spent (${remaining:,.2f} remaining of ${budget:,.2f})."
        analysis = f"Your spending in {destination} is well-controlled. You currently have sufficient buffer for planned and spontaneous activities."
        saving_tips = [
            "Maintain your current daily pacing to finish the journey comfortably under budget.",
            "Reserve a 10% emergency buffer for unforeseen travel needs or special mementos.",
            "Check local museum discount days or bundled attraction passes for bonus savings."
        ]

    category_allocations = {
        "Accommodation": "Target 35-40% of overall budget",
        "Food & Dining": "Target 25-30% of overall budget",
        "Activities & Tours": "Target 15-20% of overall budget",
        "Transport": "Target 10-15% of overall budget",
        "Contingency / Other": "Target 5-10% of overall budget"
    }

    return AIBudgetAdviceResponse(
        trip_id=req.trip_id,
        status=status_code,
        summary=summary,
        analysis=analysis,
        saving_tips=saving_tips,
        category_allocations=category_allocations
    )
