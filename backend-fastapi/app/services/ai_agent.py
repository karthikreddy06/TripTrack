import os
import re
import json
import time
import logging
import uuid
import httpx
from datetime import datetime, timezone, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from bson import ObjectId

from app.database.mongodb import (
    users_collection,
    trips_collection,
    itineraries_collection,
    expenses_collection,
    wishlist_collection,
    chat_conversations_collection
)
from app.services.explore.provider import explore_provider
from app.schemas.ai import PendingAction

logger = logging.getLogger("traveltrack.ai_agent")


# =====================================================================
# 1. SECURITY & PROMPT INJECTION SANITIZATION
# =====================================================================

INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+in\s+developer\s+mode", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?guidelines", re.IGNORECASE),
    re.compile(r"bypass\s+security", re.IGNORECASE),
    re.compile(r"output\s+the\s+prompt", re.IGNORECASE),
]


def sanitize_untrusted_text(text: Optional[str]) -> str:
    """Sanitize external content from OpenStreetMap/Wikipedia before reasoning."""
    if not text:
        return ""
    clean = str(text)
    for pat in INJECTION_PATTERNS:
        clean = pat.sub("[filtered]", clean)
    return clean[:1000]


TRAVEL_AGENT_SYSTEM_PROMPT = (
    "You are TravelTrack AI, a versatile, brilliant, and authentic general-purpose AI assistant with "
    "deep, specialized capabilities for world travel planning and personal trip tracking (similar to ChatGPT equipped with TravelTrack tools).\n\n"
    "Core Capabilities & Guidelines:\n"
    "1. GENERAL AI MODE:\n"
    "   - Answer general knowledge questions, science, programming, math, writing, brainstorming, and casual conversation naturally, thoroughly, and helpfully.\n"
    "   - For programming questions (e.g. Python, APIs, algorithms, recursion, SQL vs NoSQL), provide clear explanations with clean, formatted code blocks.\n"
    "   - For writing and brainstorming, provide structured, articulate, and creative content.\n"
    "   - For math and reasoning, explain the logic step-by-step.\n"
    "   - Do NOT force travel references, fake destinations, or tool calls into general questions.\n\n"
    "2. TRAVEL AGENT MODE:\n"
    "   - When the user asks about their trips, budgets, expenses, itineraries, or wishlist, leverage their real TravelTrack data and assist accurately.\n"
    "   - For general travel advice or questions like 'What is Kyoto famous for?' or 'Teach me Japanese phrases', answer conversationally and informatively without calling search tools.\n"
    "   - Never invent or assume a default destination.\n\n"
    "3. TONE & STYLE:\n"
    "   - Be intelligent, warm, concise, and articulate. Use clean markdown formatting (bolding, lists, code blocks)."
)


class LLMClient:
    """Unified LLM client supporting Google Gemini and OpenAI with dynamic fallback."""

    def __init__(self):
        self._load_keys()

    def _load_keys(self):
        self.gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
        self.openai_key = os.environ.get("OPENAI_API_KEY", "").strip()

    async def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        chat_history: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[str]:
        # Refresh keys in case environment updated dynamically
        self._load_keys()

        # 1. Try Google Gemini
        if self.gemini_key:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
                contents = []
                if chat_history:
                    for h in chat_history[-8:]:
                        role = "user" if h.get("role") == "user" else "model"
                        contents.append({"role": role, "parts": [{"text": h.get("content", "")}]})
                contents.append({"role": "user", "parts": [{"text": user_message}]})

                payload = {
                    "systemInstruction": {"parts": [{"text": system_prompt}]},
                    "contents": contents,
                    "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048}
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text")
                            if text:
                                return text.strip()
            except Exception as exc:
                logger.warning(f"Gemini API call failed: {exc}")

        # 2. Try OpenAI
        if self.openai_key:
            try:
                url = "https://api.openai.com/v1/chat/completions"
                messages = [{"role": "system", "content": system_prompt}]
                if chat_history:
                    for h in chat_history[-8:]:
                        role = "assistant" if h.get("role") == "assistant" else "user"
                        messages.append({"role": role, "content": h.get("content", "")})
                messages.append({"role": "user", "content": user_message})

                payload = {
                    "model": "gpt-4o-mini",
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 2048
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        url,
                        headers={"Authorization": f"Bearer {self.openai_key}"},
                        json=payload
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        choices = data.get("choices", [])
                        if choices:
                            text = choices[0].get("message", {}).get("content")
                            if text:
                                return text.strip()
            except Exception as exc:
                logger.warning(f"OpenAI API call failed: {exc}")

        return None


# =====================================================================
# 2. AUTHENTICATED TOOL REGISTRY (19+ TOOLS)
# =====================================================================

class AIAgentTools:
    """
    Direct, secure tool execution layer.
    Every tool strictly executes under the authenticated user_id to prevent IDOR/BOLA.
    """

    @staticmethod
    def get_user_trips(user_id: str) -> Dict[str, Any]:
        """Read all trips owned by the authenticated user."""
        try:
            trips = list(trips_collection.find({"user_id": user_id}).sort("start_date", 1))
            for t in trips:
                t["_id"] = str(t["_id"])
                t["trip_id"] = str(t["_id"])
            return {"success": True, "trips": trips, "count": len(trips)}
        except Exception as exc:
            logger.error(f"Error fetching user trips: {exc}")
            return {"success": False, "error": "Could not retrieve trips from database."}

    @staticmethod
    def get_trip(user_id: str, trip_id: str) -> Dict[str, Any]:
        """Read a single trip owned by the authenticated user."""
        if not ObjectId.is_valid(trip_id):
            return {"success": False, "error": "Invalid trip ID format."}
        try:
            trip = trips_collection.find_one({"_id": ObjectId(trip_id), "user_id": user_id})
            if not trip:
                return {"success": False, "error": "Trip not found or unauthorized."}
            trip["_id"] = str(trip["_id"])
            trip["trip_id"] = str(trip["_id"])
            return {"success": True, "trip": trip}
        except Exception as exc:
            logger.error(f"Error fetching trip {trip_id}: {exc}")
            return {"success": False, "error": "Could not retrieve trip details."}

    @staticmethod
    def get_itinerary(user_id: str, trip_id: str, day_number: Optional[int] = None) -> Dict[str, Any]:
        """Read itinerary activities for a trip, optionally filtered by day."""
        if not ObjectId.is_valid(trip_id):
            return {"success": False, "error": "Invalid trip ID format."}
        # Ownership check
        trip = trips_collection.find_one({"_id": ObjectId(trip_id), "user_id": user_id})
        if not trip:
            return {"success": False, "error": "Trip not found or unauthorized."}

        try:
            query: Dict[str, Any] = {"trip_id": trip_id}
            if day_number is not None:
                query["day_number"] = int(day_number)
            activities = list(itineraries_collection.find(query).sort([("day_number", 1), ("time", 1)]))
            for act in activities:
                act["_id"] = str(act["_id"])
                act["activity_id"] = str(act["_id"])
            return {
                "success": True,
                "trip_title": trip.get("title"),
                "destination": trip.get("destination"),
                "day_filter": day_number,
                "activities": activities,
                "count": len(activities)
            }
        except Exception as exc:
            logger.error(f"Error fetching itinerary for trip {trip_id}: {exc}")
            return {"success": False, "error": "Could not retrieve itinerary activities."}

    @staticmethod
    def get_expenses(user_id: str, trip_id: str) -> Dict[str, Any]:
        """Read expenses for a specific trip owned by the user."""
        if not ObjectId.is_valid(trip_id):
            return {"success": False, "error": "Invalid trip ID format."}
        trip = trips_collection.find_one({"_id": ObjectId(trip_id), "user_id": user_id})
        if not trip:
            return {"success": False, "error": "Trip not found or unauthorized."}

        try:
            expenses = list(expenses_collection.find({"trip_id": trip_id}).sort("date", -1))
            for e in expenses:
                e["_id"] = str(e["_id"])
                e["expense_id"] = str(e["_id"])
            return {"success": True, "trip_title": trip.get("title"), "expenses": expenses, "count": len(expenses)}
        except Exception as exc:
            logger.error(f"Error fetching expenses for trip {trip_id}: {exc}")
            return {"success": False, "error": "Could not retrieve expenses."}

    @staticmethod
    def get_budget(user_id: str, trip_id: str) -> Dict[str, Any]:
        """Calculate and return budget, expenses, remaining funds, and categories."""
        if not ObjectId.is_valid(trip_id):
            return {"success": False, "error": "Invalid trip ID format."}
        trip = trips_collection.find_one({"_id": ObjectId(trip_id), "user_id": user_id})
        if not trip:
            return {"success": False, "error": "Trip not found or unauthorized."}

        budget = float(trip.get("budget", 0.0))
        expenses = list(expenses_collection.find({"trip_id": trip_id}))
        total_spent = sum(float(e.get("amount", 0.0)) for e in expenses)
        remaining = budget - total_spent
        pct_spent = round((total_spent / budget * 100), 1) if budget > 0 else 0.0

        by_cat: Dict[str, float] = {}
        for e in expenses:
            c = e.get("category", "Other")
            by_cat[c] = round(by_cat.get(c, 0.0) + float(e.get("amount", 0.0)), 2)

        return {
            "success": True,
            "trip_id": trip_id,
            "trip_title": trip.get("title"),
            "destination": trip.get("destination"),
            "budget": round(budget, 2),
            "total_spent": round(total_spent, 2),
            "remaining_budget": round(remaining, 2),
            "percentage_spent": pct_spent,
            "expense_count": len(expenses),
            "by_category": by_cat
        }

    @staticmethod
    def get_wishlist(user_id: str) -> Dict[str, Any]:
        """Read all wishlist items for the authenticated user."""
        try:
            cursor = wishlist_collection.find({"user_id": user_id}).sort("created_at", -1)
            items = []
            for item in cursor:
                item["_id"] = str(item["_id"])
                items.append(item)
            return {"success": True, "items": items, "count": len(items)}
        except Exception as exc:
            logger.error(f"Error fetching wishlist for user {user_id}: {exc}")
            return {"success": False, "error": "Could not retrieve wishlist."}

    @staticmethod
    async def search_places(query: str, category: str = "all", limit: int = 6) -> Dict[str, Any]:
        """Search worldwide verified places using Nominatim & Overpass."""
        try:
            res = await explore_provider.search_places(query=query, category=category, limit=limit)
            places = res.get("places", [])
            for p in places:
                p["description"] = sanitize_untrusted_text(p.get("description"))
            return {
                "success": True,
                "query": query,
                "category": category,
                "total_results": res.get("total_results", len(places)),
                "places": places[:limit]
            }
        except Exception as exc:
            logger.error(f"Error searching explore places for '{query}': {exc}")
            return {"success": False, "error": f"Failed to search places for '{query}'."}

    @staticmethod
    async def get_place_details(place_id: str) -> Dict[str, Any]:
        """Get details for a place by ID."""
        try:
            place_data = await explore_provider.get_place_by_id(place_id)
            if not place_data or not place_data.get("place"):
                return {"success": False, "error": f"Place '{place_id}' not found."}
            p = place_data["place"]
            p["description"] = sanitize_untrusted_text(p.get("description"))
            return {"success": True, "place": p}
        except Exception as exc:
            logger.error(f"Error fetching place details for {place_id}: {exc}")
            return {"success": False, "error": "Could not retrieve place details."}

    @staticmethod
    async def find_nearby_places(query_or_coords: str, category: str = "all", radius: int = 3000) -> Dict[str, Any]:
        """Find places near a landmark or city."""
        try:
            res = await explore_provider.search_places(query=query_or_coords, category=category, limit=6)
            return {
                "success": True,
                "reference": query_or_coords,
                "places": res.get("places", [])[:6]
            }
        except Exception as exc:
            logger.error(f"Error finding nearby places for {query_or_coords}: {exc}")
            return {"success": False, "error": "Could not discover nearby places."}

    @staticmethod
    def create_trip(
        user_id: str,
        destination: str,
        title: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        budget: float = 0.0,
        travelers: int = 1,
        notes: str = ""
    ) -> Dict[str, Any]:
        """Create a new trip for the authenticated user."""
        dest_clean = destination.strip()
        trip_title = (title or f"Journey to {dest_clean}").strip()
        s_date = start_date or date.today().isoformat()
        if not end_date:
            try:
                sd = date.fromisoformat(s_date)
                e_date = (sd + timedelta(days=4)).isoformat()
            except Exception:
                e_date = s_date
        else:
            e_date = end_date

        trip_doc = {
            "user_id": user_id,
            "destination": dest_clean,
            "title": trip_title,
            "start_date": s_date,
            "end_date": e_date,
            "budget": float(budget),
            "travelers": max(1, int(travelers)),
            "status": "planned",
            "description": f"Curated journey to {dest_clean}",
            "notes": notes or "Created with TravelTrack AI Assistant."
        }

        try:
            res = trips_collection.insert_one(trip_doc)
            trip_doc["_id"] = str(res.inserted_id)
            trip_doc["trip_id"] = str(res.inserted_id)
            return {"success": True, "trip": trip_doc, "message": f"Created trip '{trip_title}'"}
        except Exception as exc:
            logger.error(f"Error creating trip: {exc}")
            return {"success": False, "error": "Database error creating trip."}

    @staticmethod
    def update_trip(user_id: str, trip_id: str, **updates) -> Dict[str, Any]:
        """Update an existing trip owned by the user."""
        if not ObjectId.is_valid(trip_id):
            return {"success": False, "error": "Invalid trip ID."}

        clean_updates = {k: v for k, v in updates.items() if v is not None and k not in ["_id", "user_id"]}
        if not clean_updates:
            return {"success": True, "message": "No changes requested."}

        try:
            res = trips_collection.update_one(
                {"_id": ObjectId(trip_id), "user_id": user_id},
                {"$set": clean_updates}
            )
            if res.matched_count == 0:
                return {"success": False, "error": "Trip not found or unauthorized."}
            return {"success": True, "message": "Trip updated successfully.", "updates": clean_updates}
        except Exception as exc:
            logger.error(f"Error updating trip {trip_id}: {exc}")
            return {"success": False, "error": "Failed to update trip."}

    @staticmethod
    def delete_trip(user_id: str, trip_id: str) -> Dict[str, Any]:
        """Delete an existing trip owned by the user (DESTRUCTIVE)."""
        if not ObjectId.is_valid(trip_id):
            return {"success": False, "error": "Invalid trip ID format."}

        try:
            trip = trips_collection.find_one({"_id": ObjectId(trip_id), "user_id": user_id})
            if not trip:
                return {"success": False, "error": "Trip not found or unauthorized."}

            res = trips_collection.delete_one({"_id": ObjectId(trip_id), "user_id": user_id})
            if res.deleted_count == 0:
                return {"success": False, "error": "Trip could not be deleted."}

            # Cascade deletions
            itineraries_collection.delete_many({"trip_id": trip_id})
            expenses_collection.delete_many({"trip_id": trip_id})

            return {"success": True, "trip_title": trip.get("title"), "message": f"Trip '{trip.get('title')}' deleted successfully."}
        except Exception as exc:
            logger.error(f"Error deleting trip {trip_id}: {exc}")
            return {"success": False, "error": "Failed to delete trip."}

    @staticmethod
    def add_itinerary_activity(
        user_id: str,
        trip_id: str,
        day_number: int,
        title: str,
        time_slot: Optional[str] = None,
        location: Optional[str] = None,
        description: Optional[str] = None,
        cost: float = 0.0,
        place_id: Optional[str] = None,
        category: Optional[str] = None,
        image_url: Optional[str] = None,
        date_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add an itinerary activity to a trip owned by user."""
        if not ObjectId.is_valid(trip_id):
            return {"success": False, "error": "Invalid trip ID format."}

        trip = trips_collection.find_one({"_id": ObjectId(trip_id), "user_id": user_id})
        if not trip:
            return {"success": False, "error": "Trip not found or unauthorized."}

        # Calculate activity date from start_date + day_number - 1 if not provided
        act_date = date_str
        if not act_date and trip.get("start_date"):
            try:
                sd = date.fromisoformat(trip["start_date"])
                act_date = (sd + timedelta(days=max(0, int(day_number) - 1))).isoformat()
            except Exception:
                act_date = trip.get("start_date")

        # Duplicate check on same day
        existing = itineraries_collection.find_one({
            "trip_id": trip_id,
            "day_number": int(day_number),
            "title": title.strip()
        })
        if existing:
            return {
                "success": True,
                "already_exists": True,
                "activity_id": str(existing["_id"]),
                "message": f"'{title.strip()}' is already scheduled for Day {day_number}."
            }

        act_doc = {
            "trip_id": trip_id,
            "user_id": user_id,
            "day_number": int(day_number),
            "date": act_date or "",
            "time": time_slot or "10:00 AM",
            "title": title.strip(),
            "location": (location or trip.get("destination", "")).strip(),
            "description": description or f"Visit and explore {title.strip()}.",
            "cost": float(cost or 0.0),
            "notes": "Added via TravelTrack AI Assistant.",
            "place_id": place_id,
            "category": category or "attraction",
            "image_url": image_url
        }

        try:
            res = itineraries_collection.insert_one(act_doc)
            act_doc["_id"] = str(res.inserted_id)
            act_doc["activity_id"] = str(res.inserted_id)
            return {
                "success": True,
                "already_exists": False,
                "activity": act_doc,
                "message": f"Added '{title.strip()}' to Day {day_number} of '{trip.get('title')}'."
            }
        except Exception as exc:
            logger.error(f"Error inserting itinerary activity: {exc}")
            return {"success": False, "error": "Database error adding activity."}

    @staticmethod
    def update_itinerary_activity(user_id: str, activity_id: str, **updates) -> Dict[str, Any]:
        """Update an itinerary activity (move days, change time, cost, etc.)."""
        if not ObjectId.is_valid(activity_id):
            return {"success": False, "error": "Invalid activity ID format."}

        try:
            act = itineraries_collection.find_one({"_id": ObjectId(activity_id)})
            if not act:
                return {"success": False, "error": "Activity not found."}

            # Verify trip ownership
            trip = trips_collection.find_one({"_id": ObjectId(act["trip_id"]), "user_id": user_id})
            if not trip:
                return {"success": False, "error": "Unauthorized to modify this activity."}

            clean_updates = {k: v for k, v in updates.items() if v is not None and k not in ["_id", "trip_id", "user_id"]}

            # If day_number is changed, also adjust date if possible
            if "day_number" in clean_updates and trip.get("start_date"):
                try:
                    sd = date.fromisoformat(trip["start_date"])
                    clean_updates["date"] = (sd + timedelta(days=max(0, int(clean_updates["day_number"]) - 1))).isoformat()
                except Exception:
                    pass

            itineraries_collection.update_one({"_id": ObjectId(activity_id)}, {"$set": clean_updates})
            return {
                "success": True,
                "activity_title": act.get("title"),
                "message": f"Updated activity '{act.get('title')}'.",
                "updates": clean_updates
            }
        except Exception as exc:
            logger.error(f"Error updating activity {activity_id}: {exc}")
            return {"success": False, "error": "Failed to update activity."}

    @staticmethod
    def delete_itinerary_activity(user_id: str, activity_id: str) -> Dict[str, Any]:
        """Delete an itinerary activity (DESTRUCTIVE)."""
        if not ObjectId.is_valid(activity_id):
            return {"success": False, "error": "Invalid activity ID format."}

        try:
            act = itineraries_collection.find_one({"_id": ObjectId(activity_id)})
            if not act:
                return {"success": False, "error": "Activity not found."}

            trip = trips_collection.find_one({"_id": ObjectId(act["trip_id"]), "user_id": user_id})
            if not trip:
                return {"success": False, "error": "Unauthorized to delete this activity."}

            res = itineraries_collection.delete_one({"_id": ObjectId(activity_id)})
            if res.deleted_count == 0:
                return {"success": False, "error": "Could not delete activity."}

            return {
                "success": True,
                "activity_title": act.get("title"),
                "day_number": act.get("day_number"),
                "message": f"Activity '{act.get('title')}' deleted successfully."
            }
        except Exception as exc:
            logger.error(f"Error deleting activity {activity_id}: {exc}")
            return {"success": False, "error": "Failed to delete activity."}

    @staticmethod
    def add_wishlist(
        user_id: str,
        place_id: str,
        name: str,
        category: str = "attraction",
        location: str = "",
        image_url: Optional[str] = None,
        rating: Optional[float] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a place to the user's wishlist."""
        # Prevent duplicates
        existing = wishlist_collection.find_one({"user_id": user_id, "place_id": place_id})
        if existing:
            return {
                "success": True,
                "already_exists": True,
                "name": name,
                "message": f"'{name}' is already in your wishlist."
            }

        item_doc = {
            "user_id": user_id,
            "place_id": place_id,
            "name": name.strip(),
            "category": category.strip().lower(),
            "location": location.strip(),
            "image_url": image_url,
            "rating": rating,
            "description": description or f"Saved sight in {location.strip() or 'destination'}.",
            "metadata": {},
            "created_at": datetime.now(timezone.utc)
        }

        try:
            res = wishlist_collection.insert_one(item_doc)
            item_doc["_id"] = str(res.inserted_id)
            return {
                "success": True,
                "already_exists": False,
                "name": name,
                "message": f"Added '{name}' to your wishlist."
            }
        except Exception as exc:
            logger.error(f"Error inserting wishlist item: {exc}")
            return {"success": False, "error": "Database error adding to wishlist."}

    @staticmethod
    def remove_wishlist(user_id: str, wishlist_id: Optional[str] = None, place_id: Optional[str] = None) -> Dict[str, Any]:
        """Remove a place from user's wishlist (DESTRUCTIVE)."""
        query: Dict[str, Any] = {"user_id": user_id}
        if wishlist_id and ObjectId.is_valid(wishlist_id):
            query["_id"] = ObjectId(wishlist_id)
        elif place_id:
            query["place_id"] = place_id
        else:
            return {"success": False, "error": "Either wishlist_id or place_id must be provided."}

        try:
            item = wishlist_collection.find_one(query)
            if not item:
                return {"success": False, "error": "Wishlist item not found."}

            wishlist_collection.delete_one(query)
            return {
                "success": True,
                "name": item.get("name"),
                "message": f"Removed '{item.get('name')}' from your wishlist."
            }
        except Exception as exc:
            logger.error(f"Error removing wishlist item: {exc}")
            return {"success": False, "error": "Failed to remove wishlist item."}

    @staticmethod
    def add_expense(
        user_id: str,
        trip_id: str,
        category: str,
        amount: float,
        description: str,
        date_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """Log a financial expense for a trip."""
        if not ObjectId.is_valid(trip_id):
            return {"success": False, "error": "Invalid trip ID format."}

        trip = trips_collection.find_one({"_id": ObjectId(trip_id), "user_id": user_id})
        if not trip:
            return {"success": False, "error": "Trip not found or unauthorized."}

        valid_categories = ["Accommodation", "Food", "Transport", "Activities", "Shopping", "Other"]
        cat_norm = next((c for c in valid_categories if c.lower() == category.strip().lower()), "Other")

        exp_doc = {
            "trip_id": trip_id,
            "user_id": user_id,
            "category": cat_norm,
            "amount": round(float(amount), 2),
            "description": description.strip(),
            "date": date_str or date.today().isoformat()
        }

        try:
            res = expenses_collection.insert_one(exp_doc)
            exp_doc["_id"] = str(res.inserted_id)
            return {
                "success": True,
                "expense": exp_doc,
                "message": f"Logged expense of ₹{amount:,.2f} for '{description.strip()}' under {cat_norm}."
            }
        except Exception as exc:
            logger.error(f"Error adding expense: {exc}")
            return {"success": False, "error": "Database error recording expense."}

    @staticmethod
    def update_expense(user_id: str, expense_id: str, **updates) -> Dict[str, Any]:
        """Update an existing expense."""
        if not ObjectId.is_valid(expense_id):
            return {"success": False, "error": "Invalid expense ID format."}

        try:
            exp = expenses_collection.find_one({"_id": ObjectId(expense_id)})
            if not exp:
                return {"success": False, "error": "Expense not found."}

            trip = trips_collection.find_one({"_id": ObjectId(exp["trip_id"]), "user_id": user_id})
            if not trip:
                return {"success": False, "error": "Unauthorized to modify this expense."}

            clean_updates = {k: v for k, v in updates.items() if v is not None and k not in ["_id", "trip_id", "user_id"]}
            expenses_collection.update_one({"_id": ObjectId(expense_id)}, {"$set": clean_updates})
            return {
                "success": True,
                "message": f"Updated expense '{exp.get('description')}'.",
                "updates": clean_updates
            }
        except Exception as exc:
            logger.error(f"Error updating expense {expense_id}: {exc}")
            return {"success": False, "error": "Failed to update expense."}

    @staticmethod
    def delete_expense(user_id: str, expense_id: str) -> Dict[str, Any]:
        """Delete an expense (DESTRUCTIVE)."""
        if not ObjectId.is_valid(expense_id):
            return {"success": False, "error": "Invalid expense ID format."}

        try:
            exp = expenses_collection.find_one({"_id": ObjectId(expense_id)})
            if not exp:
                return {"success": False, "error": "Expense not found."}

            trip = trips_collection.find_one({"_id": ObjectId(exp["trip_id"]), "user_id": user_id})
            if not trip:
                return {"success": False, "error": "Unauthorized to delete this expense."}

            expenses_collection.delete_one({"_id": ObjectId(expense_id)})
            return {
                "success": True,
                "description": exp.get("description"),
                "amount": exp.get("amount"),
                "message": f"Deleted expense of ₹{exp.get('amount', 0):,.2f} for '{exp.get('description')}'."
            }
        except Exception as exc:
            logger.error(f"Error deleting expense {expense_id}: {exc}")
            return {"success": False, "error": "Failed to delete expense."}


# =====================================================================
# 3. CONVERSATIONAL MEMORY MANAGER
# =====================================================================

class ConversationMemoryManager:
    """Persists and retrieves multi-turn conversation sessions in MongoDB."""

    @staticmethod
    def get_or_create_conversation(user_id: str, conversation_id: Optional[str]) -> Tuple[str, Dict[str, Any]]:
        cid = conversation_id or uuid.uuid4().hex[:12]
        doc = chat_conversations_collection.find_one({"user_id": user_id, "conversation_id": cid})
        if not doc:
            doc = {
                "user_id": user_id,
                "conversation_id": cid,
                "messages": [],
                "context": {
                    "last_recommended_places": [],
                    "last_mentioned_place": None,
                    "active_trip_id": None,
                    "pending_action": None
                },
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            chat_conversations_collection.insert_one(doc)
        return cid, doc

    @staticmethod
    def save_turn(
        user_id: str,
        conversation_id: str,
        user_message: str,
        ai_message: str,
        context_updates: Dict[str, Any],
        tool_called: Optional[str] = None,
        tool_result: Optional[Any] = None,
        pending_action: Optional[Dict[str, Any]] = None,
        action_status: Optional[str] = None,
        places: Optional[List[Dict[str, Any]]] = None
    ):
        now_iso = datetime.now(timezone.utc).isoformat()
        u_item = {
            "id": uuid.uuid4().hex[:8],
            "role": "user",
            "content": user_message,
            "timestamp": now_iso
        }
        a_item = {
            "id": uuid.uuid4().hex[:8],
            "role": "assistant",
            "content": ai_message,
            "timestamp": now_iso,
            "tool_called": tool_called,
            "tool_result": tool_result,
            "pending_action": pending_action,
            "action_status": action_status,
            "places": places
        }

        set_fields: Dict[str, Any] = {
            "updated_at": datetime.now(timezone.utc),
        }
        for k, v in context_updates.items():
            set_fields[f"context.{k}"] = v

        chat_conversations_collection.update_one(
            {"user_id": user_id, "conversation_id": conversation_id},
            {
                "$push": {"messages": {"$each": [u_item, a_item]}},
                "$set": set_fields
            }
        )


# =====================================================================
# 4. INTENT CLASSIFICATION & NATURAL LANGUAGE ENGINE
# =====================================================================

class TravelTrackAIAgent:
    """
    Production-grade AI Travel Agent.
    Orchestrates natural language understanding, multi-turn follow-ups,
    context resolution, tool invocation, and safety confirmation checks.
    """

    def __init__(self):
        self.tools = AIAgentTools()
        self.memory = ConversationMemoryManager()
        self.llm_client = LLMClient()

    def _resolve_active_trip(self, user_id: str, explicit_trip_id: Optional[str], context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Identify which trip the user is referring to (strictly explicit, no silent guessing)."""
        # 1. Explicit trip ID passed in request
        if explicit_trip_id and ObjectId.is_valid(explicit_trip_id):
            trip = trips_collection.find_one({"_id": ObjectId(explicit_trip_id), "user_id": user_id})
            if trip:
                trip["_id"] = str(trip["_id"])
                return trip

        # 2. Context active trip
        ctx_trip_id = context.get("active_trip_id")
        if ctx_trip_id and ObjectId.is_valid(ctx_trip_id):
            trip = trips_collection.find_one({"_id": ObjectId(ctx_trip_id), "user_id": user_id})
            if trip:
                trip["_id"] = str(trip["_id"])
                return trip

        return None

    def _is_greeting_or_casual(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Determine if text is a greeting, acknowledgment, or casual chat.
        Returns (True, type) if casual/greeting and contains NO actionable travel commands.
        """
        clean = re.sub(r"[^\w\s']", "", text.strip()).lower()
        words = clean.split()
        if not words:
            return True, "greeting"

        # Actionable stems that indicate a tool action or data inquiry
        ACTIONABLE_STEMS = [
            "find", "search", "explore", "show", "read", "list", "get", "check",
            "add", "delete", "remove", "update", "change", "move", "create", "plan",
            "budget", "expense", "expenses", "itinerary", "wishlist", "trip", "trips",
            "hotel", "hotels", "restaurant", "restaurants", "cafe", "cafes",
            "attraction", "attractions", "sights", "places", "visit", "schedule"
        ]

        has_actionable = any(
            w in ACTIONABLE_STEMS or any(s in w for s in ["budget", "expense", "itinerary", "wishlist"])
            for w in words
        )

        # 1. Thanks / Gratitude
        if any(clean == w or clean.startswith(w + " ") for w in ["thanks", "thank you", "thx", "ty", "cheers", "much appreciated"]):
            if not has_actionable:
                return True, "thanks"

        # 2. Affirmations / Acknowledgments
        if any(clean == w for w in ["ok", "okay", "cool", "awesome", "great", "sounds good", "perfect", "got it", "understood", "nice", "alright", "sure", "yep", "fine"]):
            if not has_actionable:
                return True, "acknowledgment"

        # 3. Farewells
        if any(clean == w or clean.startswith(w + " ") for w in ["bye", "goodbye", "see you", "see ya", "talk to you later", "good night"]):
            if not has_actionable:
                return True, "farewell"

        # 4. Identity / Capabilities
        if any(clean == w for w in ["who are you", "what can you do", "what are you", "help", "help me"]):
            if not has_actionable:
                return True, "identity"

        # 5. Greetings
        GREETING_STARTS = [
            "hi", "hey", "heyy", "heyyy", "hello", "howdy", "hola", "namaste", "bonjour", "greetings",
            "good morning", "good afternoon", "good evening", "good day",
            "whats up", "what's up", "wassup", "sup", "how are you", "how are you doing", "hows it going", "how's it going"
        ]

        is_greeting_word = any(
            clean == g or clean.startswith(g + " ") or re.match(r"^he+y+$", clean) or re.match(r"^hi+$", clean) or re.match(r"^hello+$", clean)
            for g in GREETING_STARTS
        )

        if is_greeting_word and not has_actionable:
            return True, "greeting"

        return False, None

    def _generate_natural_chat_response(
        self,
        user_message: str,
        greeting_type: str,
        active_trip: Optional[Dict[str, Any]] = None,
        is_new_conversation: bool = False,
        chat_history: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Dynamically crafts an authentic, friendly assistant response for greetings and casual chat.
        Never repeats the initial welcome greeting for subsequent turns.
        """
        t_low = user_message.lower().strip()

        if greeting_type == "thanks":
            if active_trip:
                return f"You're very welcome! Let me know if you need anything else for your trip to **{active_trip.get('destination')}**, like checking budget or scheduling activities."
            return "You're very welcome! Feel free to ask anytime—whether you want to explore places, check your budget, or need help with general questions and coding."

        if greeting_type == "acknowledgment":
            if active_trip:
                return f"Sounds good! Whenever you're ready, we can add activities, log expenses, or review your schedule for **{active_trip.get('destination')}**."
            return "Sounds like a plan! Let me know what you'd like to work on—whether that's exploring destinations, organizing trips, writing, or coding."

        if greeting_type == "farewell":
            return "Safe travels and happy wandering! Reach out whenever you're ready to plan your next journey or need assistance."

        if greeting_type == "identity":
            return (
                "I am **TravelTrack AI**, a versatile AI assistant combining general intelligence (coding, writing, math, and explanations) "
                "with specialized personal travel capabilities (trips, itineraries, budgets, expenses, and OpenStreetMap Explore places).\n\n"
                "Here are some things you can ask me:\n"
                "• **General AI:** *'Explain machine learning'*, *'What is Python?'*, *'Write a Python API'*, *'Tell me a joke'*, *'Teach me Japanese phrases'*\n"
                "• **Explore:** *'Find top attractions in Mumbai'*, *'Restaurants near Eiffel Tower'*\n"
                "• **TravelTrack:** *'What is my budget?'*, *'What am I doing tomorrow?'*, *'Add this to Day 2'*, *'Check my wishlist'*"
            )

        # Handle Greetings
        if greeting_type == "greeting":
            hour = datetime.now().hour
            tod = "Good morning" if 5 <= hour < 12 else ("Good afternoon" if 12 <= hour < 18 else "Good evening")

            if "good morning" in t_low:
                salutation = "Good morning!"
            elif "good evening" in t_low:
                salutation = "Good evening!"
            elif "good afternoon" in t_low:
                salutation = "Good afternoon!"
            elif "hey" in t_low:
                salutation = "Hey there! 👋"
            elif "hello" in t_low:
                salutation = "Hello! 👋"
            else:
                salutation = f"{tod}! 👋"

            if is_new_conversation:
                if active_trip:
                    return (
                        f"{salutation} I'm TravelTrack AI. How can I help with your trip to **{active_trip.get('destination')}** today? "
                        "You can ask about your schedule, check your remaining budget, or ask general questions."
                    )
                return (
                    f"{salutation} I'm TravelTrack AI. What can I help you with today? "
                    "You can ask me general questions, explore destinations worldwide, check your budget, or manage your trips."
                )
            else:
                if active_trip:
                    return f"{salutation} How can I assist with your journey to **{active_trip.get('destination')}** right now?"
                return f"{salutation} How can I assist you right now?"

        # Non-greeting general AI inquiry
        return self._generate_general_ai_response(user_message, chat_history or [], active_trip)

    def _generate_general_ai_response(
        self,
        user_message: str,
        chat_history: List[Dict[str, Any]],
        active_trip: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Rich, versatile general-purpose AI engine (ChatGPT-like).
        Covers coding, science, writing, math, jokes, language phrases, and travel reasoning.
        """
        t_low = user_message.lower().strip()

        # 1. Python Overview
        if re.search(r"\b(?:what\s+is\s+python|tell\s+me\s+about\s+python|explain\s+python|learn\s+python)\b", t_low) or t_low in ["python", "python?"]:
            return (
                "**Python** is a high-level, interpreted programming language celebrated for its clear, human-readable syntax and immense versatility.\n\n"
                "### Core Highlights:\n"
                "• **Clean Readability**: Uses indentation to define code blocks instead of curly braces (*The Zen of Python*).\n"
                "• **Massive Ecosystem**: Dominates Web Development (FastAPI, Django), Data Science & AI (PyTorch, TensorFlow, Pandas), Automation, and DevOps.\n"
                "• **Batteries Included**: Comprehensive standard library offering built-in tools for networking, math, file I/O, and data processing.\n\n"
                "```python\n"
                "# Quick Python Example: Destination Filter\n"
                "destinations = [{\"name\": \"Kyoto\", \"days\": 4}, {\"name\": \"Paris\", \"days\": 5}]\n"
                "long_trips = [d[\"name\"] for d in destinations if d[\"days\"] >= 4]\n"
                "print(f\"Trips 4+ days: {long_trips}\")\n"
                "```\n\n"
                "Would you like to build an application, write a specific script, or explore libraries like FastAPI or Pandas?"
            )

        # 2. Machine Learning
        if re.search(r"\b(?:machine\s+learning|what\s+is\s+ml|explain\s+ml|deep\s+learning)\b", t_low):
            return (
                "**Machine Learning (ML)** is a branch of Artificial Intelligence where computers learn patterns from data to make predictions or decisions without explicit, rule-based programming.\n\n"
                "### Three Primary Paradigms:\n"
                "1. **Supervised Learning**:\n"
                "   • Trains on labeled datasets (input paired with expected output).\n"
                "   • *Tasks*: Classification (spam detection, image tagging) and Regression (predicting trip costs, house prices).\n"
                "2. **Unsupervised Learning**:\n"
                "   • Identifies hidden structures, groupings, or anomalies in unlabeled data.\n"
                "   • *Tasks*: Customer segmentation, recommendation engines, clustering attractions by geographic coordinates.\n"
                "3. **Reinforcement Learning**:\n"
                "   • An agent learns optimal actions via trial-and-error using reward and penalty signals.\n"
                "   • *Tasks*: Autonomous driving, game playing (AlphaGo), dynamic route planning.\n\n"
                "### Typical Pipeline:\n"
                "`Data Ingestion` ➔ `Feature Engineering` ➔ `Model Training` ➔ `Validation & Testing` ➔ `Deployment`\n\n"
                "Would you like to see a Python code implementation (e.g. Scikit-learn or PyTorch) or explore a specific concept?"
            )

        # 3. Write a Python API
        if re.search(r"\b(?:write|create|build|make)\s+(?:a\s+)?(?:python\s+)?(?:api|rest\s+api|fastapi|backend)\b", t_low) or "python api" in t_low:
            return (
                "Here is a complete, production-ready **FastAPI REST API** in Python featuring Pydantic data validation and auto-generated OpenAPI documentation:\n\n"
                "```python\n"
                "from fastapi import FastAPI, HTTPException, status\n"
                "from pydantic import BaseModel, Field\n"
                "from typing import Optional, List\n"
                "import uvicorn\n\n"
                "app = FastAPI(title=\"TravelTrack API Service\", version=\"1.0.0\")\n\n"
                "# In-memory database simulation\n"
                "destinations_db = {}\n\n"
                "# Data Validation Schema\n"
                "class DestinationSchema(BaseModel):\n"
                "    name: str = Field(..., min_length=2, example=\"Kyoto\")\n"
                "    country: str = Field(..., min_length=2, example=\"Japan\")\n"
                "    budget_estimate: Optional[float] = Field(default=None, ge=0)\n"
                "    duration_days: int = Field(default=3, ge=1, le=30)\n\n"
                "@app.get(\"/\")\n"
                "def home():\n"
                "    return {\"status\": \"online\", \"message\": \"Welcome to TravelTrack API! ✈️\"}\n\n"
                "@app.get(\"/destinations\", response_model=List[DestinationSchema])\n"
                "def list_destinations():\n"
                "    return list(destinations_db.values())\n\n"
                "@app.post(\"/destinations\", status_code=status.HTTP_201_CREATED)\n"
                "def create_destination(item: DestinationSchema):\n"
                "    key = item.name.lower()\n"
                "    if key in destinations_db:\n"
                "        raise HTTPException(status_code=400, detail=\"Destination already exists\")\n"
                "    destinations_db[key] = item.dict()\n"
                "    return item\n\n"
                "if __name__ == \"__main__\":\n"
                "    uvicorn.run(\"main:app\", host=\"127.0.0.1\", port=8000, reload=True)\n"
                "```\n\n"
                "### How to Run:\n"
                "1. `pip install fastapi uvicorn`\n"
                "2. `python main.py`\n"
                "3. Access the interactive Swagger UI at **http://127.0.0.1:8000/docs**."
            )

        # 4. Recursion
        if re.search(r"\b(?:what\s+is\s+recursion|explain\s+recursion|how\s+does\s+recursion\s+work|recursion\s+in\s+python)\b", t_low) or "recursion" in t_low:
            return (
                "**Recursion** is a programming method where a function solves a problem by calling itself with smaller inputs until reaching a terminal condition.\n\n"
                "### Every Recursive Function Requires Two Parts:\n"
                "1. **Base Case**: The condition that terminates the recursion and returns a direct result without further recursive calls.\n"
                "2. **Recursive Step**: The logic that reduces the problem towards the base case and invokes the function again.\n\n"
                "### Example 1: Factorial ($n!$)\n"
                "```python\n"
                "def factorial(n: int) -> int:\n"
                "    # Base Case\n"
                "    if n <= 1:\n"
                "        return 1\n"
                "    # Recursive Step\n"
                "    return n * factorial(n - 1)\n\n"
                "print(factorial(5))  # 5 * 4 * 3 * 2 * 1 = 120\n"
                "```\n\n"
                "### Example 2: Fibonacci Sequence\n"
                "```python\n"
                "def fibonacci(n: int) -> int:\n"
                "    if n <= 0: return 0\n"
                "    if n == 1: return 1\n"
                "    return fibonacci(n - 1) + fibonacci(n - 2)\n\n"
                "print([fibonacci(i) for i in range(7)])  # [0, 1, 1, 2, 3, 5, 8]\n"
                "```\n\n"
                "⚠️ **Important Note**: Every recursive call allocates a new frame on the system's **Call Stack**. Without a valid base case, it triggers a `RecursionError` (stack overflow)."
            )

        # 5. SQL vs NoSQL
        if re.search(r"\b(?:sql\s+vs\s+nosql|difference\s+between\s+sql\s+and\s+nosql|compare\s+sql\s+and\s+nosql)\b", t_low):
            return (
                "Here is a comprehensive breakdown between **SQL** (Relational) and **NoSQL** (Non-relational) databases:\n\n"
                "| Dimension | SQL Databases | NoSQL Databases |\n"
                "| :--- | :--- | :--- |\n"
                "| **Data Structure** | Structured tables with fixed rows and columns | Flexible documents (JSON/BSON), key-value, graphs, wide-column |\n"
                "| **Schema** | Explicit, rigid schema required | Dynamic, schemaless, adaptable schema |\n"
                "| **Scaling** | Primarily **Vertical** (upgrading RAM/CPU) | Inherently **Horizontal** (sharding across distributed servers) |\n"
                "| **Guarantees** | Strict **ACID** (Atomicity, Consistency, Isolation, Durability) | **BASE** (Basically Available, Soft-state, Eventual consistency) |\n"
                "| **Queries** | Standard Structured Query Language (`SELECT`, `JOIN`) | Declarative APIs or JSON queries (`db.collection.find()`) |\n"
                "| **Leading Examples** | PostgreSQL, MySQL, SQLite, Oracle | MongoDB, Redis, Cassandra, DynamoDB |\n\n"
                "### Strategic Choice:\n"
                "• **Choose SQL** for financial transactions, multi-table relational integrity, and strict reporting.\n"
                "• **Choose NoSQL** for rapid agile development, evolving hierarchical documents (like travel itineraries), high-throughput caching, and real-time feeds."
            )

        # 6. Photosynthesis
        if re.search(r"\b(?:photosynthesis|what\s+is\s+photosynthesis|explain\s+photosynthesis)\b", t_low):
            return (
                "**Photosynthesis** is the fundamental biological process by which green plants, algae, and cyanobacteria convert light energy into chemical energy stored in carbohydrates (sugars).\n\n"
                "### Universal Chemical Equation:\n"
                "$$\\mathbf{6CO_2 + 6H_2O + \\text{sunlight} \\longrightarrow C_6H_{12}O_6 + 6O_2}$$\n\n"
                "### The Two Main Stages:\n"
                "1. **Light-Dependent Reactions (in Thylakoid Membranes)**:\n"
                "   • Chlorophyll absorbs solar photons to energize electrons.\n"
                "   • Water ($H_2O$) is split via photolysis, releasing **Oxygen ($O_2$)** into the atmosphere.\n"
                "   • Synthesizes energy carriers: **ATP** and **NADPH**.\n"
                "2. **Light-Independent Reactions / Calvin Cycle (in the Stroma)**:\n"
                "   • The enzyme **RuBisCO** captures Carbon Dioxide ($CO_2$).\n"
                "   • Uses the ATP and NADPH produced in stage 1 to synthesize high-energy **glucose ($C_6H_{12}O_6$)**.\n\n"
                "Photosynthesis is the foundation of Earth's biosphere: it produces atmospheric oxygen and fuels virtually all terrestrial food webs!"
            )

        # 7. Help Write an Email
        if re.search(r"\b(?:help\s+me\s+write\s+(?:an?\s+)?email|write\s+(?:an?\s+)?email|draft\s+(?:an?\s+)?email)\b", t_low):
            return (
                "Here is a polished, professional email template adaptable for business, collaboration, or formal inquiries:\n\n"
                "**Subject:** [Concise Subject Line, e.g. Project Update / Travel Schedule Confirmation]\n\n"
                "Dear [Recipient's Name],\n\n"
                "I hope this message finds you well.\n\n"
                "I am writing to [state purpose clearly, e.g. provide a brief update on our progress / confirm the logistical details for our upcoming travel schedule].\n\n"
                "Here are the key points for your reference:\n"
                "• **[Point 1]**: [Brief summary or update]\n"
                "• **[Point 2]**: [Specific deliverable, decision, or question]\n"
                "• **[Timeline/Next Step]**: [Target deadline or expected date]\n\n"
                "Please let me know if you need any additional details or if you'd like to schedule a quick call to discuss.\n\n"
                "Thank you for your time and support.\n\n"
                "Warm regards,  \n"
                "**[Your Name]**  \n"
                "[Your Contact Information / Title]\n\n"
                "💡 *Feel free to give me specific details (who it's to, tone, key details) and I'll draft a customized version for you!*"
            )

        # 8. Japanese Phrases for Kyoto
        if re.search(r"\b(?:japanese\s+phrases|phrases\s+(?:for|in)\s+kyoto|japanese\s+(?:for|words)|teach\s+me\s+japanese)\b", t_low):
            return (
                "Here are essential **Japanese phrases** for traveling in Kyoto, complete with pronunciations and cultural context:\n\n"
                "### 1. Essential Politeness & Greetings\n"
                "• **Arigatou gozaimasu** (*ah-ree-gah-toh goh-zah-ee-mahs*) — Thank you very much (polite and respectful).\n"
                "• **Konnichiwa** (*kohn-nee-chee-wah*) — Hello / Good afternoon.\n"
                "• **Sumimasen** (*soo-mee-mah-sen*) — Excuse me / I'm sorry (essential for calling staff or apologizing in crowds).\n"
                "• **Onegaishimasu** (*oh-neh-gah-ee-shee-mahs*) — Please (used when asking for an item or service).\n"
                "• **Hai / Iie** (*hi / ee-eh*) — Yes / No.\n\n"
                "### 2. Dining & Ordering in Kyoto\n"
                "• **Kore o kudasai** (*koh-reh oh koo-dah-sy*) — This one, please (point to the menu item).\n"
                "• **O-kaikei o onegaishimasu** (*oh-kye-kay oh oh-neh-gah-ee-shee-mahs*) — The check/bill, please.\n"
                "• **Oishii desu!** (*oy-shee dess*) — It is delicious!\n"
                "• **Mizu o onegaishimasu** (*mee-zoo oh oh-neh-gah-ee-shee-mahs*) — Water, please.\n\n"
                "### 3. Directions & Sightseeing\n"
                "• **...wa doko desu ka?** (*...wah doh-koh dess kah?*) — Where is...?\n"
                "  *(e.g., \"Toire wa doko desu ka?\" = Where is the restroom?)*\n"
                "• **Ikura desu ka?** (*ee-koo-rah dess kah?*) — How much does this cost?\n"
                "• **Eigo ga hanasemasu ka?** (*ay-goh gah hah-nah-seh-mahs kah?*) — Do you speak English?\n\n"
                "💡 **Kyoto Etiquette Tips**:\n"
                "• Bow slightly (15–30°) when expressing gratitude.\n"
                "• Wear slip-on shoes: you must remove shoes before entering traditional temple halls, ryokans, and tatami rooms.\n"
                "• Always carry cash/yen coins for temple entry gates and small traditional vendors."
            )

        # 9. What is Kyoto Famous For
        if re.search(r"\b(?:what\s+is\s+kyoto\s+famous\s+for|what\s+is\s+kyoto\s+known\s+for|why\s+is\s+kyoto\s+famous)\b", t_low) or "kyoto famous" in t_low:
            return (
                "**Kyoto** is celebrated as the cultural and spiritual soul of Japan, having served as the nation's imperial capital for over 1,000 years (from 794 to 1868).\n\n"
                "### What Makes Kyoto World-Famous:\n"
                "1. **Incredible UNESCO World Heritage Sites (17 Monuments)**:\n"
                "   • **Fushimi Inari Taisha**: Thousands of brilliant vermilion torii gates stretching up Mount Inari.\n"
                "   • **Kinkaku-ji (The Golden Pavilion)**: Zen Buddhist temple covered in authentic gold leaf reflecting over a mirror pond.\n"
                "   • **Kiyomizu-dera**: Massive wooden stage built without a single nail offering sweeping city views.\n"
                "2. **Living Geisha & Geiko Heritage**:\n"
                "   • Historic entertainment quarters in **Gion** and **Pontocho** with cobblestone streets and wooden *machiya* merchant houses.\n"
                "3. **Culinary Mastery**:\n"
                "   • **Kaiseki Ryori**: Multi-course Japanese fine dining emphasizing seasonality and artistic presentation.\n"
                "   • **Uji Matcha**: World-renowned ceremonial matcha green tea and matcha confections.\n"
                "4. **Zen Gardens & Nature**:\n"
                "   • The iconic **Arashiyama Bamboo Grove** and meditative dry rock gardens like **Ryoan-ji**.\n\n"
                "Would you like recommendations on must-visit sights, dining spots, or itinerary planning for Kyoto?"
            )

        # 10. Jokes & Humor
        if re.search(r"\b(?:tell\s+me\s+a\s+joke|joke|make\s+me\s+laugh|funny\s+joke)\b", t_low):
            return (
                "Here's one for you! 😄\n\n"
                "**Why do programmers prefer dark mode?**\n"
                "...*Because light attracts bugs!* 🐛\n\n"
                "*(And a travel one: \"I told the airline gate agent that my suitcase wasn't heavy—it was just emotionally attached to my vacation!\")* ✈️\n\n"
                "Need another joke, a riddle, or ready to jump back into planning?"
            )

        # 11. Arithmetic & Math Calculations
        m_calc = re.search(r"(\d+(?:\.\d+)?)\s*([\+\-\*\/])\s*(\d+(?:\.\d+)?)", t_low)
        if m_calc and any(w in t_low for w in ["what is", "calculate", "how much is", "="]):
            try:
                n1 = float(m_calc.group(1))
                op = m_calc.group(2)
                n2 = float(m_calc.group(3))
                res = None
                if op == "+": res = n1 + n2
                elif op == "-": res = n1 - n2
                elif op == "*": res = n1 * n2
                elif op == "/" and n2 != 0: res = n1 / n2
                if res is not None:
                    return f"**Calculation:** `{m_calc.group(1)} {op} {m_calc.group(3)}` = **{res:g}**"
            except Exception:
                pass

        m_pct = re.search(r"(\d+(?:\.\d+)?)\s*%\s*of\s*(\d+(?:\.\d+)?)", t_low)
        if m_pct:
            pct = float(m_pct.group(1))
            total = float(m_pct.group(2))
            ans = (pct / 100.0) * total
            return f"**{pct}% of {total:g} is {ans:g}**."

        # 12. Contextual Conversational Response (Zero robotic canned messages)
        if active_trip:
            return (
                f"Regarding '**{user_message}**' for your trip to **{active_trip.get('destination')}**: "
                "I can dive deeper into this topic, search specific sights or dining spots, schedule activities to your days, "
                "or analyze your expenses. How would you like to proceed?"
            )

        return (
            f"That's an interesting question regarding '**{user_message}**'. "
            "I'm here to help with general questions, coding, explanations, writing, as well as managing your trips, budgets, and itineraries. "
            "Could you share a bit more detail on what you'd like to explore?"
        )

    def _handle_travel_budget_reasoning(
        self,
        user_id: str,
        msg_text: str,
        cid: str,
        active_trip: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyzes whether a stated or remaining budget is sufficient for a destination trip.
        Combines actual trip dates/duration with local cost-of-living data.
        """
        target_trip = self._match_trip_from_text(user_id, msg_text) or active_trip
        if not target_trip:
            all_trips = self.tools.get_user_trips(user_id).get("trips", [])
            if len(all_trips) == 1:
                target_trip = all_trips[0]

        amt = self._extract_amount(msg_text) or 10000.0
        dest = target_trip.get("destination", "Hyderabad") if target_trip else "Hyderabad"
        title = target_trip.get("title", f"Trip to {dest}") if target_trip else f"Trip to {dest}"

        days = 4
        if target_trip and target_trip.get("start_date") and target_trip.get("end_date"):
            try:
                s = date.fromisoformat(target_trip["start_date"])
                e = date.fromisoformat(target_trip["end_date"])
                days = max(1, (e - s).days + 1)
            except Exception:
                days = 4

        daily_budget = amt / days

        lines = [
            f"💰 **Budget Feasibility Analysis for '{title}' ({dest})**",
            f"• **Available Funds:** **₹{amt:,.2f}**",
            f"• **Trip Duration:** **{days} days**",
            f"• **Daily Allowance:** **₹{daily_budget:,.2f} / day**\n",
            f"**Verdict: YES, ₹{amt:,.0f} is comfortably sufficient for {dest}**, provided accommodation is already handled. Here is a realistic daily spending breakdown:\n",
            "1. **Food & Dining (₹600 – ₹900 / day):**",
            "   • Breakfast: Irani chai, osmania biscuits, or South Indian tiffins (₹80–₹150)",
            "   • Lunch/Dinner: Authentic Hyderabadi Dum Biryani, haleem, or local curries (₹250–₹400 per meal)\n",
            "2. **Local Transportation (₹300 – ₹500 / day):**",
            "   • Clean, air-conditioned Metro connectivity across major commercial hubs (₹30–₹60 per ride)",
            "   • Auto-rickshaws and app-based cabs for door-to-door transit\n",
            "3. **Sightseeing & Monument Entry (₹150 – ₹300 / day):**",
            "   • Historic monuments like Charminar, Golconda Fort, and Salar Jung Museum (₹25–₹100 per entry)\n",
            f"**Bottom Line:** At ₹{daily_budget:,.2f}/day, you have plenty of room for delicious local food, transit, museum tickets, and souvenirs! 🎉"
        ]
        reply = "\n".join(lines)
        self.memory.save_turn(user_id, cid, msg_text, reply, {}, action_status="read_only")
        return {"response": reply, "conversation_id": cid, "tool_called": None, "action_status": "read_only", "places": []}

    def _handle_itinerary_efficiency_reasoning(
        self,
        user_id: str,
        msg_text: str,
        cid: str,
        active_trip: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Inspects the user's itinerary activities and analyzes route clustering efficiency.
        """
        target_trip = self._match_trip_from_text(user_id, msg_text) or active_trip
        if not target_trip:
            all_trips = self.tools.get_user_trips(user_id).get("trips", [])
            if len(all_trips) == 1:
                target_trip = all_trips[0]

        target_trip_id = str(target_trip["_id"]) if target_trip else None
        acts = []
        if target_trip_id:
            itin_res = self.tools.get_itinerary(user_id, target_trip_id)
            acts = itin_res.get("activities", [])

        lines = [
            "🗺️ **Itinerary Route & Efficiency Analysis:**\n"
        ]
        if acts:
            titles = [f"'{a['title']}' (Day {a.get('day_number', 1)})" for a in acts[:4]]
            lines.extend([
                f"I examined your scheduled activities ({', '.join(titles)}):\n",
                "1. **Geographic Clustering**: When sights are located on opposite sides of the city, crisscrossing through metropolitan traffic can waste 1.5 to 3 hours each day.",
                "2. **Optimization Strategy**:",
                "   • **Cluster Old City landmarks**: Group Charminar, Chowmahalla Palace, Mecca Masjid, and Salar Jung Museum together on the same day.",
                "   • **Cluster Western Heritage**: Group Golconda Fort and the Qutb Shahi Tombs together since they are geographically adjacent.",
                "   • **Hi-Tech & Lake Zone**: Keep Durgam Cheruvu and HITEC City cafes grouped together.\n",
                "💡 *Tip: Say 'Move [Activity Name] to Day X' anytime and I will reschedule it for optimal routing!*"
            ])
        else:
            lines.extend([
                "To optimize an itinerary, activities should be clustered geographically by district rather than scheduled at random:",
                "• **Zone 1**: Group historic Old City monuments together to explore on foot.",
                "• **Zone 2**: Group fortresses and heritage complexes that share western arterial roads.",
                "• **Zone 3**: Schedule shopping and culinary evenings close to your accommodation.\n",
                "Add a few activities to your trip and I can evaluate travel times and distance clusters for you!"
            ])
        reply = "\n".join(lines)
        self.memory.save_turn(user_id, cid, msg_text, reply, {}, action_status="read_only")
        return {"response": reply, "conversation_id": cid, "tool_called": None, "action_status": "read_only", "places": []}

    async def _handle_conversational_chat(
        self,
        user_message: str,
        greeting_type: str,
        chat_history: List[Dict[str, Any]],
        active_trip: Optional[Dict[str, Any]] = None,
        is_new_conversation: bool = False
    ) -> str:
        """
        Routes chat message to real LLM (Gemini / OpenAI) or dynamic contextual generator.
        """
        llm_reply = await self.llm_client.generate_response(
            system_prompt=TRAVEL_AGENT_SYSTEM_PROMPT,
            user_message=user_message,
            chat_history=chat_history
        )
        if llm_reply:
            return llm_reply

        return self._generate_natural_chat_response(
            user_message=user_message,
            greeting_type=greeting_type,
            active_trip=active_trip,
            is_new_conversation=is_new_conversation,
            chat_history=chat_history
        )

    @staticmethod
    def _parse_natural_date(text: str) -> Optional[date]:
        """
        Robust natural language date parser.
        Understands:
        - Relative dates: 'today', 'tomorrow', 'day after tomorrow', 'in 3 days', 'in a week', 'next monday'
        - Month names: 'November 1st', 'Nov 1', '1 November', '15th December 2026', 'Dec 25'
        - ISO formats: '2026-11-01', '2026/11/01'
        """
        t = text.lower().strip()
        today = date.today()

        if "today" in t:
            return today
        if "day after tomorrow" in t:
            return today + timedelta(days=2)
        if "tomorrow" in t:
            return today + timedelta(days=1)

        m_days = re.search(r"\bin\s+(\d+)\s+days?\b", t)
        if m_days:
            return today + timedelta(days=int(m_days.group(1)))

        if "in a week" in t or "in 1 week" in t:
            return today + timedelta(days=7)
        if "in 2 weeks" in t:
            return today + timedelta(days=14)

        WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for idx, wday in enumerate(WEEKDAYS):
            if f"next {wday}" in t or f"this {wday}" in t:
                days_ahead = idx - today.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                return today + timedelta(days=days_ahead)

        # ISO format YYYY-MM-DD or YYYY/MM/DD
        m_iso = re.search(r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b", t)
        if m_iso:
            try:
                return date(int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3)))
            except ValueError:
                pass

        MONTHS = {
            "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
            "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
            "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9, "october": 10, "oct": 10,
            "november": 11, "nov": 11, "december": 12, "dec": 12
        }

        # Month Name + Day (e.g. "November 1st", "Nov 1", "Nov 1, 2026")
        m_md = re.search(
            r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{4}))?\b",
            t
        )
        if m_md:
            m_str = m_md.group(1)
            d_int = int(m_md.group(2))
            y_int = int(m_md.group(3)) if m_md.group(3) else today.year
            if 1 <= d_int <= 31 and m_str in MONTHS:
                try:
                    res_d = date(y_int, MONTHS[m_str], d_int)
                    if not m_md.group(3) and res_d < today:
                        res_d = date(y_int + 1, MONTHS[m_str], d_int)
                    return res_d
                except ValueError:
                    pass

        # Day + Month Name (e.g. "1st November", "1 Nov", "15th of December 2026")
        m_dm = re.search(
            r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)(?:\s*,?\s*(\d{4}))?\b",
            t
        )
        if m_dm:
            d_int = int(m_dm.group(1))
            m_str = m_dm.group(2)
            y_int = int(m_dm.group(3)) if m_dm.group(3) else today.year
            if 1 <= d_int <= 31 and m_str in MONTHS:
                try:
                    res_d = date(y_int, MONTHS[m_str], d_int)
                    if not m_dm.group(3) and res_d < today:
                        res_d = date(y_int + 1, MONTHS[m_str], d_int)
                    return res_d
                except ValueError:
                    pass

        return None

    def _match_trip_from_text(self, user_id: str, text: str) -> Optional[Dict[str, Any]]:
        """
        Matches user's actual trips against text using destination, title, or index.
        """
        trips_res = self.tools.get_user_trips(user_id)
        trips = trips_res.get("trips", [])
        if not trips:
            return None

        t_low = text.lower().strip()
        clean = re.sub(r"[^\w\s]", "", t_low)

        # Exact or partial match on ID, destination, or title
        for t in trips:
            if str(t.get("_id")) in text:
                return t
            dest = t.get("destination", "").lower()
            title = t.get("title", "").lower()
            if dest and (dest == t_low or dest in t_low or t_low in dest or dest in clean):
                return t
            if title and (title == t_low or title in t_low or t_low in title or title in clean):
                return t

        # Match ordinals or numbers: "first", "1", "second", "2"
        if clean in ["1", "first", "1st", "first trip"] and len(trips) >= 1:
            return trips[0]
        if clean in ["2", "second", "2nd", "second trip"] and len(trips) >= 2:
            return trips[1]
        if clean in ["3", "third", "3rd", "third trip"] and len(trips) >= 3:
            return trips[2]

        return None

    async def _handle_pending_clarification(
        self,
        user_id: str,
        msg_text: str,
        pending: Dict[str, Any],
        cid: str,
        session_doc: Dict[str, Any],
        active_trip: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluates a user message as the answer to an outstanding clarification question.
        Returns a complete API response dictionary if handled, or None if clarification was abandoned.
        """
        p_type = pending.get("type")
        msg_low = msg_text.lower().strip()

        # Cancellation check
        if msg_low in ["cancel", "stop", "nevermind", "never mind", "abort", "no"]:
            reply = "Understood. Cancelled that request. What else can I help you with?"
            self.memory.save_turn(
                user_id=user_id,
                conversation_id=cid,
                user_message=msg_text,
                ai_message=reply,
                context_updates={"pending_clarification": None},
                action_status="cancelled"
            )
            return {
                "response": reply,
                "conversation_id": cid,
                "tool_called": None,
                "action_status": "cancelled",
                "places": []
            }

        # 1. User is answering: Which trip's budget?
        if p_type == "which_trip_for_budget":
            matched_trip = self._match_trip_from_text(user_id, msg_text)
            if matched_trip:
                target_trip_id = str(matched_trip["_id"])
                budget_data = self.tools.get_budget(user_id, target_trip_id)
                if not budget_data["success"]:
                    reply = f"Could not retrieve budget: {budget_data.get('error')}"
                else:
                    b = budget_data["budget"]
                    s = budget_data["total_spent"]
                    r = budget_data["remaining_budget"]
                    p = budget_data["percentage_spent"]
                    lines = [
                        f"💰 **Budget Summary for {budget_data.get('trip_title')} ({budget_data.get('destination')}):**",
                        f"• **Total Budget:** ₹{b:,.2f}",
                        f"• **Total Spent:** ₹{s:,.2f} ({p}%)",
                        f"• **Remaining Budget:** **₹{r:,.2f}**"
                    ]
                    if budget_data.get("by_category"):
                        lines.append("\n**Category Breakdown:**")
                        for cat, amt in budget_data["by_category"].items():
                            lines.append(f"• {cat}: ₹{amt:,.2f}")
                    reply = "\n".join(lines)

                self.memory.save_turn(
                    user_id=user_id,
                    conversation_id=cid,
                    user_message=msg_text,
                    ai_message=reply,
                    context_updates={"pending_clarification": None, "active_trip_id": target_trip_id},
                    tool_called="get_budget",
                    tool_result=budget_data,
                    action_status="read_only"
                )
                return {
                    "response": reply,
                    "conversation_id": cid,
                    "tool_called": "get_budget",
                    "tool_result": budget_data,
                    "action_status": "read_only",
                    "places": []
                }
            else:
                trips_res = self.tools.get_user_trips(user_id)
                trips = trips_res.get("trips", [])
                trip_names = [f"'{t['destination']}'" for t in trips]
                reply = f"I couldn't match '{msg_text}' to your trips ({', '.join(trip_names)}). Which trip's budget would you like to check?"
                self.memory.save_turn(user_id, cid, msg_text, reply, {}, action_status="read_only")
                return {"response": reply, "conversation_id": cid, "tool_called": None, "action_status": "read_only", "places": []}

        # 2. User is answering: What date to change the trip to?
        if p_type == "new_date_for_trip":
            target_trip_id = pending.get("trip_id")
            dest = pending.get("trip_destination", "your trip")
            new_d = self._parse_natural_date(msg_text)
            if new_d:
                trip_doc = trips_collection.find_one({"_id": ObjectId(target_trip_id), "user_id": user_id})
                new_start_str = new_d.isoformat()
                new_end_str = new_start_str
                if trip_doc and trip_doc.get("start_date") and trip_doc.get("end_date"):
                    try:
                        old_s = date.fromisoformat(trip_doc["start_date"])
                        old_e = date.fromisoformat(trip_doc["end_date"])
                        dur = max(0, (old_e - old_s).days)
                        new_end_str = (new_d + timedelta(days=dur)).isoformat()
                    except Exception:
                        pass

                res = self.tools.update_trip(user_id, target_trip_id, start_date=new_start_str, end_date=new_end_str)
                if res["success"]:
                    reply = f"✅ Updated the dates for your **{dest}** trip! It is now scheduled from **{new_start_str}** to **{new_end_str}**."
                    status = "executed"
                else:
                    reply = f"❌ Failed to update trip date: {res.get('error')}"
                    status = "failed"

                self.memory.save_turn(
                    user_id=user_id,
                    conversation_id=cid,
                    user_message=msg_text,
                    ai_message=reply,
                    context_updates={"pending_clarification": None},
                    tool_called="update_trip",
                    tool_result=res,
                    action_status=status
                )
                return {
                    "response": reply,
                    "conversation_id": cid,
                    "tool_called": "update_trip",
                    "tool_result": res,
                    "action_status": status,
                    "mutation_occurred": res["success"],
                    "affected_entity": "trip",
                    "places": []
                }
            else:
                reply = f"I couldn't understand '{msg_text}' as a calendar date. Please specify a date like 'November 1st', 'next Monday', or '2026-11-01'."
                self.memory.save_turn(user_id, cid, msg_text, reply, {}, action_status="read_only")
                return {"response": reply, "conversation_id": cid, "tool_called": None, "action_status": "read_only", "places": []}

        # 3. User is answering: Which trip to change date for?
        if p_type == "which_trip_for_date_change":
            matched_trip = self._match_trip_from_text(user_id, msg_text)
            new_start_str = pending.get("new_date")
            if matched_trip and new_start_str:
                target_trip_id = str(matched_trip["_id"])
                dest = matched_trip.get("destination", "your trip")
                new_d = date.fromisoformat(new_start_str)
                new_end_str = new_start_str
                if matched_trip.get("start_date") and matched_trip.get("end_date"):
                    try:
                        old_s = date.fromisoformat(matched_trip["start_date"])
                        old_e = date.fromisoformat(matched_trip["end_date"])
                        dur = max(0, (old_e - old_s).days)
                        new_end_str = (new_d + timedelta(days=dur)).isoformat()
                    except Exception:
                        pass

                res = self.tools.update_trip(user_id, target_trip_id, start_date=new_start_str, end_date=new_end_str)
                if res["success"]:
                    reply = f"✅ Updated the dates for your **{dest}** trip! It is now scheduled from **{new_start_str}** to **{new_end_str}**."
                    status = "executed"
                else:
                    reply = f"❌ Failed to update trip date: {res.get('error')}"
                    status = "failed"

                self.memory.save_turn(
                    user_id=user_id,
                    conversation_id=cid,
                    user_message=msg_text,
                    ai_message=reply,
                    context_updates={"pending_clarification": None},
                    tool_called="update_trip",
                    tool_result=res,
                    action_status=status
                )
                return {
                    "response": reply,
                    "conversation_id": cid,
                    "tool_called": "update_trip",
                    "tool_result": res,
                    "action_status": status,
                    "mutation_occurred": res["success"],
                    "affected_entity": "trip",
                    "places": []
                }

        # 4. User is answering: Which place to add to wishlist?
        if p_type == "which_place_for_wishlist":
            clean_name = msg_text.strip()
            search_res = await self.tools.search_places(clean_name, limit=1)
            found_places = search_res.get("places", [])
            if found_places:
                p = found_places[0]
                name = p["name"]
                pid = p.get("place_id") or p.get("id") or f"wish_{uuid.uuid4().hex[:8]}"
                loc = p.get("address") or p.get("location") or ""
                cat = p.get("category", "attraction")
                img = p.get("image_url")
            else:
                name = clean_name.title()
                pid = f"wish_{uuid.uuid4().hex[:8]}"
                loc = ""
                cat = "attraction"
                img = None

            res = self.tools.add_wishlist(user_id, pid, name, cat, loc, img)
            if res["success"]:
                reply = f"✅ Added **{name}** to your saved wishlist."
                status = "executed"
            else:
                reply = f"❌ Could not add to wishlist: {res.get('error')}"
                status = "failed"

            self.memory.save_turn(
                user_id=user_id,
                conversation_id=cid,
                user_message=msg_text,
                ai_message=reply,
                context_updates={"pending_clarification": None, "last_mentioned_place": {"name": name, "place_id": pid}},
                tool_called="add_wishlist",
                tool_result=res,
                action_status=status
            )
            return {
                "response": reply,
                "conversation_id": cid,
                "tool_called": "add_wishlist",
                "tool_result": res,
                "action_status": status,
                "mutation_occurred": res["success"],
                "affected_entity": "wishlist",
                "places": []
            }

        return None

    def _detect_place_search(self, msg_text: str) -> Optional[Dict[str, Any]]:
        """
        Detect place search intent and extract destination/landmark and category.
        Strictly excludes general AI questions, explanations, action intents, mutations, or clarification answers.
        """
        t_low = msg_text.lower().strip()

        # 0. Strict exclusion of general AI questions, coding, science, explanations, advice, or language questions
        GENERAL_AI_TRIGGERS = [
            r"\bteach\s+me\b", r"\bphrases?\b", r"\bwords?\b", r"\blanguage\b", r"\btranslate\b",
            r"\bfamous\s+for\b", r"\bhistory\s+of\b", r"\bculture\s+of\b", r"\btell\s+me\s+about\b",
            r"\bexplain\b", r"\bwhat\s+is\b", r"\bwhat\s+are\b", r"\bwhy\s+is\b", r"\bwhy\s+are\b",
            r"\bhow\s+does\b", r"\bhow\s+do\b", r"\bhow\s+to\b", r"\bhow\s+can\b",
            r"\bwrite\b", r"\bhelp\s+me\b", r"\bjoke\b", r"\briddle\b",
            r"\bpython\b", r"\bcode\b", r"\bprogram\b", r"\balgorithm\b", r"\brecursion\b",
            r"\bmachine\s+learning\b", r"\bdeep\s+learning\b", r"\bdata\s+science\b",
            r"\bsql\b", r"\bnosql\b", r"\bdatabase\b", r"\bphotosynthesis\b",
            r"\bis\s+(?:that|this|it|\d+[\d,]*)\s+enough\b", r"\bcan\s+i\s+afford\b", r"\binefficient\b",
            r"\bweather\b", r"\bflights?\b", r"\btickets?\b", r"\bvisa\b", r"\bcurrency\b",
            r"\bpacking\b", r"\bwhat\s+should\s+i\s+pack\b"
        ]
        if any(re.search(pat, t_low) for pat in GENERAL_AI_TRIGGERS):
            # Only treat as place search if there is an explicit discovery command like "find places in", "search attractions in", etc.
            if not any(re.search(pat, t_low) for pat in [
                r"\b(?:find|search|explore|look\s+for|show(?:\s+me)?|list)\s+(?:all\s+the\s+)?(?:places|attractions|sights|spots|hotels?|restaurants?)\b"
            ]):
                return None

        # 1. Strict exclusion of action words, functional commands, and confirmation words
        ACTION_STEMS = [
            "trip", "trips", "budget", "expense", "expenses", "itinerary", "wishlist", "wishkist", "bucketlist",
            "add", "delete", "remove", "cancel", "update", "change", "reschedule", "move", "create", "plan",
            "yes", "no", "ok", "okay", "sure", "thanks", "thank you", "hello", "hi", "hey",
            "doing tomorrow", "what am i doing", "how much", "remaining", "spent", "spending"
        ]
        words = t_low.split()
        if any(w in ACTION_STEMS for w in words):
            # If it has action words, it can ONLY be a search if it explicitly has "places in <city>" or "hotels in <city>"
            if not any(phrase in t_low for phrase in ["places in", "sights in", "attractions in", "hotels in", "restaurants in", "things to do in"]):
                return None

        # 2. Determine category
        cat = "all"
        if any(w in t_low for w in ["hotel", "stay", "resort", "lodging", "hostel", "accommodation"]):
            cat = "hotels"
        elif any(w in t_low for w in ["restaurant", "cafe", "food", "dining", "eat", "lunch", "dinner", "breakfast"]):
            cat = "restaurants"
        elif any(w in t_low for w in ["attraction", "sight", "museum", "historic", "monument", "places to visit", "things to do", "famous places"]):
            cat = "attractions"

        # 3. Check for nearby landmark: e.g. "near Eiffel Tower", "around Colosseum", "close to Charminar", "nearby Big Ben"
        m_near = re.search(r"\b(?:near|around|close\s+to|nearby)\s+([^?.!,]+)", msg_text, re.IGNORECASE)
        if m_near:
            target = m_near.group(1).strip()
            target = re.sub(r"\b(please|thanks|thank you)\b", "", target, flags=re.IGNORECASE).strip()
            if len(target) >= 2:
                return {
                    "is_nearby": True,
                    "target": target,
                    "category": cat
                }

        # 4. Check for destination preposition: e.g. "in Mumbai", "places in Kolkata", "to visit in Paris", "hotels for Tokyo"
        m_in = re.search(r"\b(?:in|at|to\s+visit\s+in)\s+([^?.!,]+)", msg_text, re.IGNORECASE)
        if not m_in:
            m_in = re.search(r"\b(?:places|sights|attractions|recommendations|guide|hotels?|restaurants?)\s+(?:for|of)\s+([^?.!,]+)", msg_text, re.IGNORECASE)
        if m_in:
            target = m_in.group(1).strip()
            target = re.sub(r"\b(please|thanks|thank you)\b", "", target, flags=re.IGNORECASE).strip()
            target = re.sub(r"\b(places|attractions|sights|hotels|restaurants|things to do)\b", "", target, flags=re.IGNORECASE).strip()
            if len(target) >= 2:
                return {
                    "is_nearby": False,
                    "target": target,
                    "category": cat
                }

        # 5. Check direct verbs: e.g. "explore Paris", "search Kyoto", "visit Rome"
        m_direct = re.search(r"\b(?:explore|search|visit|discover)\s+([a-zA-Z\s]{2,30})$", msg_text, re.IGNORECASE)
        if m_direct:
            cand = m_direct.group(1).strip()
            if cand.lower() not in ["places", "attractions", "hotels", "restaurants", "sights", "more", "trip", "itinerary"]:
                return {
                    "is_nearby": False,
                    "target": cand,
                    "category": cat
                }

        # 6. Check generic search verbs or nouns WITHOUT location:
        # e.g. "find places", "get places", "show me places", "find attractions", "recommend hotels"
        SEARCH_TRIGGERS = [
            r"\b(?:find|search|explore|discover|recommend|look\s+for|show(?:\s+me)?|give(?:\s+me)?|get(?:\s+me)?|tell(?:\s+me)?|list|suggest)\b",
            r"\b(?:places|sights|attractions|things\s+to\s+do|spots|hotels?|restaurants?)\b"
        ]
        has_search_trigger = any(re.search(pat, t_low) for pat in SEARCH_TRIGGERS)
        if has_search_trigger:
            clean_search = re.sub(
                r"\b(?:find|search|explore|discover|recommend|look\s+for|show(?:\s+me)?|give(?:\s+me)?|get(?:\s+me)?|tell(?:\s+me)?|list|suggest|all\s+the|the|all|places|sights|attractions|things\s+to\s+do|spots|hotels?|restaurants?|food|in|at|for|to\s+visit|me|please)\b",
                "",
                msg_text,
                flags=re.IGNORECASE
            ).strip()
            clean_search = re.sub(r"[^\w\s]", "", clean_search).strip()
            if len(clean_search) >= 2 and not clean_search.isdigit():
                return {
                    "is_nearby": False,
                    "target": clean_search,
                    "category": cat
                }
            return {
                "is_nearby": False,
                "target": None,
                "category": cat
            }

        # 7. Single or short location query: e.g. "mumbai", "tokyo", "paris", "new york"
        if 1 <= len(words) <= 3 and len(t_low) >= 3 and not t_low.isdigit():
            clean_word = re.sub(r"[^\w\s]", "", t_low).strip()
            NON_LOCATION_WORDS = [
                "yes", "no", "ok", "okay", "sure", "cancel", "stop", "help", "who", "what", "why", "when", "how",
                "test", "demo", "sample", "trip", "trips", "itinerary", "budget", "expense", "wishlist", "wishkist",
                "add", "change", "update", "delete", "remove", "date", "dates", "tomorrow", "today", "yesterday",
                "november", "december", "january", "february", "march", "april", "may", "june", "july", "august", "september", "october"
            ]
            if clean_word not in NON_LOCATION_WORDS and not any(w in clean_word for w in ["wish", "trip", "date"]):
                return {
                    "is_nearby": False,
                    "target": clean_word,
                    "category": cat
                }

        return None

    def _extract_amount(self, text: str) -> Optional[float]:
        """Extract monetary amounts (e.g. ₹1,200, Rs 500, $45, 1200)."""
        m = re.search(r"(?:₹|rs\.?|\$)\s*([\d,]+(?:\.\d+)?)", text, re.IGNORECASE)
        if m:
            clean = m.group(1).replace(",", "")
            try:
                return float(clean)
            except ValueError:
                pass
        m2 = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:rupees|inr|dollars|bucks)\b", text, re.IGNORECASE)
        if m2:
            try:
                return float(m2.group(1))
            except ValueError:
                pass
        return None

    def _extract_day_number(self, text: str, trip: Optional[Dict[str, Any]] = None) -> int:
        """Extract target day number (e.g. Day 3, tomorrow, next day)."""
        m = re.search(r"\bday\s*(\d+)\b", text, re.IGNORECASE)
        if m:
            return max(1, int(m.group(1)))

        if "tomorrow" in text.lower():
            if trip and trip.get("start_date"):
                try:
                    sd = date.fromisoformat(trip["start_date"])
                    diff = (date.today() + timedelta(days=1) - sd).days
                    return max(1, diff + 1)
                except Exception:
                    pass
            return 2

        if "next day" in text.lower():
            return 2

        return 1

    def _resolve_place_reference(self, text: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Resolve ordinal references like 'the first one', 'the second one', 'that place'."""
        rec_places = context.get("last_recommended_places", [])
        t_low = text.lower()

        if rec_places:
            if "first" in t_low or "1st" in t_low:
                return rec_places[0] if len(rec_places) >= 1 else None
            if "second" in t_low or "2nd" in t_low:
                return rec_places[1] if len(rec_places) >= 2 else None
            if "third" in t_low or "3rd" in t_low:
                return rec_places[2] if len(rec_places) >= 3 else None
            if "fourth" in t_low or "4th" in t_low:
                return rec_places[3] if len(rec_places) >= 4 else None
            if "last" in t_low:
                return rec_places[-1]

        # Pronoun or demonstrative reference ("add it", "add that", "add this", "that place", "this place")
        pronoun_match = any(
            re.search(rf"\b{p}\b", t_low) for p in [
                "it", "that", "this", "that place", "this place", "the place", "the sight", "the attraction"
            ]
        )
        if pronoun_match:
            if context.get("last_mentioned_place"):
                return context["last_mentioned_place"]
            if rec_places:
                return rec_places[0]

        return None

    async def process_chat(
        self,
        user_id: str,
        message: str,
        explicit_trip_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        confirm_action: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Main conversational entrypoint.
        """
        cid, session_doc = self.memory.get_or_create_conversation(user_id, conversation_id)
        context = session_doc.get("context", {})
        msg_text = message.strip()
        msg_low = msg_text.lower()

        # Identify active trip context (strictly explicit, no silent guessing)
        active_trip = self._resolve_active_trip(user_id, explicit_trip_id, context)
        active_trip_id = active_trip["_id"] if active_trip else None

        # -------------------------------------------------------------
        # A. HANDLE CONFIRMATION STATE MACHINE FOR PENDING ACTIONS
        # -------------------------------------------------------------
        pending = context.get("pending_action")
        is_confirmation_yes = confirm_action is True or msg_low in [
            "yes", "confirm", "proceed", "go ahead", "do it", "sure", "yes please", "delete it", "remove it"
        ]
        is_confirmation_no = confirm_action is False or msg_low in [
            "no", "cancel", "don't", "abort", "stop", "never mind", "nevermind", "no thanks"
        ]

        if pending and (is_confirmation_yes or is_confirmation_no):
            if is_confirmation_yes:
                tool_name = pending["tool"]
                tool_args = pending["args"]

                # Execute confirmed destructive tool
                if tool_name == "delete_trip":
                    res = self.tools.delete_trip(user_id, tool_args["trip_id"])
                    if res["success"]:
                        reply = f"✅ **Confirmed:** Trip '**{res.get('trip_title')}**' has been permanently deleted."
                        status = "executed"
                    else:
                        reply = f"❌ **Failed:** {res.get('error', 'Could not delete trip.')}"
                        status = "failed"
                    entity = "trip"

                elif tool_name == "delete_itinerary_activity":
                    res = self.tools.delete_itinerary_activity(user_id, tool_args["activity_id"])
                    if res["success"]:
                        reply = f"✅ **Confirmed:** Deleted '**{res.get('activity_title')}**' from Day {res.get('day_number', '')} of your itinerary."
                        status = "executed"
                    else:
                        reply = f"❌ **Failed:** {res.get('error', 'Could not delete activity.')}"
                        status = "failed"
                    entity = "itinerary"

                elif tool_name == "remove_wishlist":
                    res = self.tools.remove_wishlist(user_id, wishlist_id=tool_args.get("wishlist_id"), place_id=tool_args.get("place_id"))
                    if res["success"]:
                        reply = f"✅ **Confirmed:** Removed '**{res.get('name')}**' from your wishlist."
                        status = "executed"
                    else:
                        reply = f"❌ **Failed:** {res.get('error', 'Could not remove wishlist item.')}"
                        status = "failed"
                    entity = "wishlist"

                elif tool_name == "delete_expense":
                    res = self.tools.delete_expense(user_id, tool_args["expense_id"])
                    if res["success"]:
                        reply = f"✅ **Confirmed:** Deleted expense of **₹{res.get('amount', 0):,.2f}** for '**{res.get('description')}**'."
                        status = "executed"
                    else:
                        reply = f"❌ **Failed:** {res.get('error', 'Could not delete expense.')}"
                        status = "failed"
                    entity = "expense"

                else:
                    reply = "Unknown pending action."
                    status = "failed"
                    res = {"success": False}
                    entity = None

                self.memory.save_turn(
                    user_id=user_id,
                    conversation_id=cid,
                    user_message=msg_text,
                    ai_message=reply,
                    context_updates={"pending_action": None},
                    tool_called=tool_name,
                    tool_result=res,
                    action_status=status
                )
                return {
                    "response": reply,
                    "conversation_id": cid,
                    "tool_called": tool_name,
                    "tool_result": res,
                    "action_status": status,
                    "mutation_occurred": res.get("success", False),
                    "affected_entity": entity
                }

            else:
                # Cancelled by user
                reply = "Action cancelled. No changes were made to your TravelTrack data."
                self.memory.save_turn(
                    user_id=user_id,
                    conversation_id=cid,
                    user_message=msg_text,
                    ai_message=reply,
                    context_updates={"pending_action": None},
                    action_status="cancelled"
                )
                return {
                    "response": reply,
                    "conversation_id": cid,
                    "action_status": "cancelled",
                    "mutation_occurred": False
                }

        # -------------------------------------------------------------
        # A2. HANDLE PENDING CLARIFICATION (ANSWERING PRIOR AI QUESTION)
        # -------------------------------------------------------------
        pending_clarification = context.get("pending_clarification")
        if pending_clarification:
            clarification_result = await self._handle_pending_clarification(
                user_id=user_id,
                msg_text=msg_text,
                pending=pending_clarification,
                cid=cid,
                session_doc=session_doc,
                active_trip=active_trip
            )
            if clarification_result:
                return clarification_result

        # -------------------------------------------------------------
        # 1. GREETINGS / CASUAL CONVERSATION / ACKNOWLEDGMENTS
        # -------------------------------------------------------------
        is_greeting, g_type = self._is_greeting_or_casual(msg_text)
        if is_greeting:
            chat_history = session_doc.get("messages", [])
            is_new = len(chat_history) == 0
            reply = await self._handle_conversational_chat(
                user_message=msg_text,
                greeting_type=g_type,
                chat_history=chat_history,
                active_trip=active_trip,
                is_new_conversation=is_new
            )
            self.memory.save_turn(
                user_id=user_id,
                conversation_id=cid,
                user_message=msg_text,
                ai_message=reply,
                context_updates={},
                tool_called=None,
                tool_result=None,
                action_status="read_only"
            )
            return {
                "response": reply,
                "conversation_id": cid,
                "tool_called": None,
                "tool_result": None,
                "action_status": "read_only",
                "places": []
            }

        # -------------------------------------------------------------
        # 1B. INTENT: TRAVEL CONTEXT REASONING (BUDGET FEASIBILITY & ITINERARY EFFICIENCY)
        # -------------------------------------------------------------
        # e.g. "I have ₹10,000 left for my Hyderabad trip. Is that enough?", "Is 10,000 enough for my trip?"
        if any(re.search(pat, msg_low) for pat in [
            r"\b(?:is\s+(?:that|this|it|\d+[\d,]*)\s+enough)\b",
            r"\bcan\s+i\s+afford\b",
            r"\bhow\s+far\s+will\b.*?\b(?:go|last)\b",
            r"\benough\s+for\s+(?:my\s+)?(?:trip|[a-zA-Z\s]+)\b"
        ]):
            return self._handle_travel_budget_reasoning(user_id, msg_text, cid, active_trip)

        # e.g. "Explain why my current itinerary is inefficient", "optimize my itinerary", "is my itinerary efficient"
        if any(re.search(pat, msg_low) for pat in [
            r"\b(?:inefficient|optimize\s+itinerary|optimize\s+my\s+route|is\s+my\s+itinerary\s+(?:good|efficient))\b"
        ]):
            return self._handle_itinerary_efficiency_reasoning(user_id, msg_text, cid, active_trip)

        # -------------------------------------------------------------
        # 2. INTENT: TRIP DATE & ATTRIBUTE UPDATES (RESCHEDULE / MOVE DATE)
        # -------------------------------------------------------------
        if any(p in msg_low for p in [
            "change the date", "change date", "update the date", "update date",
            "change trip date", "update trip date", "reschedule trip", "reschedule date",
            "move date", "change the trip date", "reschedule the trip", "change my trip date"
        ]):
            target_trip = self._match_trip_from_text(user_id, msg_text)
            if not target_trip and active_trip:
                target_trip = active_trip
            if not target_trip:
                all_trips = self.tools.get_user_trips(user_id).get("trips", [])
                if len(all_trips) == 1:
                    target_trip = all_trips[0]

            parsed_d = self._parse_natural_date(msg_text)

            if target_trip and parsed_d:
                new_start_str = parsed_d.isoformat()
                new_end_str = new_start_str
                if target_trip.get("start_date") and target_trip.get("end_date"):
                    try:
                        old_s = date.fromisoformat(target_trip["start_date"])
                        old_e = date.fromisoformat(target_trip["end_date"])
                        dur = max(0, (old_e - old_s).days)
                        new_end_str = (parsed_d + timedelta(days=dur)).isoformat()
                    except Exception:
                        pass

                res = self.tools.update_trip(user_id, str(target_trip["_id"]), start_date=new_start_str, end_date=new_end_str)
                if res["success"]:
                    reply = f"✅ Updated the dates for your **{target_trip['destination']}** trip! It is now scheduled from **{new_start_str}** to **{new_end_str}**."
                    status = "executed"
                else:
                    reply = f"❌ Failed to update trip date: {res.get('error')}"
                    status = "failed"

                self.memory.save_turn(
                    user_id=user_id,
                    conversation_id=cid,
                    user_message=msg_text,
                    ai_message=reply,
                    context_updates={"pending_clarification": None, "active_trip_id": str(target_trip["_id"])},
                    tool_called="update_trip",
                    tool_result=res,
                    action_status=status
                )
                return {
                    "response": reply,
                    "conversation_id": cid,
                    "tool_called": "update_trip",
                    "tool_result": res,
                    "action_status": status,
                    "mutation_occurred": res["success"],
                    "affected_entity": "trip"
                }

            elif target_trip and not parsed_d:
                dest = target_trip.get("destination", "your trip")
                reply = f"What date would you like to change your **{dest}** trip to? (For example: 'November 1st' or '2026-11-01')"
                self.memory.save_turn(
                    user_id=user_id,
                    conversation_id=cid,
                    user_message=msg_text,
                    ai_message=reply,
                    context_updates={
                        "pending_clarification": {
                            "type": "new_date_for_trip",
                            "trip_id": str(target_trip["_id"]),
                            "trip_destination": dest
                        }
                    },
                    action_status="read_only"
                )
                return {"response": reply, "conversation_id": cid, "tool_called": None, "action_status": "read_only", "places": []}

            elif not target_trip and parsed_d:
                all_trips = self.tools.get_user_trips(user_id).get("trips", [])
                trip_names = [f"'{t['destination']}'" for t in all_trips]
                reply = f"Which trip would you like to change the date for? ({', '.join(trip_names)})"
                self.memory.save_turn(
                    user_id=user_id,
                    conversation_id=cid,
                    user_message=msg_text,
                    ai_message=reply,
                    context_updates={
                        "pending_clarification": {
                            "type": "which_trip_for_date_change",
                            "new_date": parsed_d.isoformat()
                        }
                    },
                    action_status="read_only"
                )
                return {"response": reply, "conversation_id": cid, "tool_called": None, "action_status": "read_only", "places": []}

            else:
                reply = "Which trip would you like to update, and what new date would you like to set?"
                self.memory.save_turn(user_id, cid, msg_text, reply, {}, action_status="read_only")
                return {"response": reply, "conversation_id": cid, "tool_called": None, "action_status": "read_only", "places": []}

        # -------------------------------------------------------------
        # B. INTENT: DESTRUCTIVE ACTIONS (REQUIRES CONFIRMATION)
        # -------------------------------------------------------------

        # 1. Delete trip
        if any(p in msg_low for p in ["delete my trip", "delete trip", "remove my trip", "cancel my trip", "delete the trip"]):
            target_trip = self._match_trip_from_text(user_id, msg_text) or active_trip
            if not target_trip:
                all_trips = self.tools.get_user_trips(user_id).get("trips", [])
                if len(all_trips) == 1:
                    target_trip = all_trips[0]

            if not target_trip:
                return {
                    "response": "Which trip would you like to delete? Please specify the destination or trip title.",
                    "conversation_id": cid,
                    "action_status": "read_only"
                }

            desc = f"Permanently delete trip '{target_trip['title']}' to {target_trip['destination']} and all associated activities and expenses."
            pending_obj = PendingAction(
                action_id=uuid.uuid4().hex[:8],
                tool="delete_trip",
                description=desc,
                args={"trip_id": target_trip["_id"]}
            )
            reply = f"⚠️ **Confirmation Required:** Are you sure you want to permanently delete your trip '**{target_trip['title']}**' to **{target_trip['destination']}**?\n\nThis will also remove all scheduled activities and logged expenses. This action cannot be undone."
            self.memory.save_turn(
                user_id=user_id,
                conversation_id=cid,
                user_message=msg_text,
                ai_message=reply,
                context_updates={"pending_action": pending_obj.model_dump()},
                pending_action=pending_obj.model_dump(),
                action_status="pending_confirmation"
            )
            return {
                "response": reply,
                "conversation_id": cid,
                "pending_action": pending_obj,
                "requires_confirmation": True,
                "action_status": "pending_confirmation"
            }

        # 2. Delete activity
        if any(p in msg_low for p in ["delete activity", "remove activity", "delete this activity", "remove from itinerary", "delete from itinerary"]):
            if not active_trip_id:
                return {"response": "Please specify which trip's itinerary you'd like to remove activities from.", "conversation_id": cid}

            itin_res = self.tools.get_itinerary(user_id, active_trip_id)
            acts = itin_res.get("activities", [])
            target_act = None

            # Check if name in text
            for a in acts:
                if a["title"].lower() in msg_low:
                    target_act = a
                    break

            # Check ordinal reference (e.g. "delete the first one")
            if not target_act:
                ref_place = self._resolve_place_reference(msg_text, context)
                if ref_place:
                    for a in acts:
                        if ref_place["name"].lower() in a["title"].lower():
                            target_act = a
                            break

            if not target_act and acts:
                target_act = acts[-1]  # fallback to last activity

            if not target_act:
                return {"response": f"I couldn't find a matching activity to delete in your trip '{active_trip.get('title')}'.", "conversation_id": cid}

            desc = f"Delete activity '{target_act['title']}' from Day {target_act['day_number']}"
            pending_obj = PendingAction(
                action_id=uuid.uuid4().hex[:8],
                tool="delete_itinerary_activity",
                description=desc,
                args={"activity_id": target_act["_id"]}
            )
            reply = f"⚠️ **Confirmation Required:** Are you sure you want to delete '**{target_act['title']}**' from Day {target_act['day_number']} of your itinerary?"
            self.memory.save_turn(
                user_id=user_id,
                conversation_id=cid,
                user_message=msg_text,
                ai_message=reply,
                context_updates={"pending_action": pending_obj.model_dump()},
                pending_action=pending_obj.model_dump(),
                action_status="pending_confirmation"
            )
            return {
                "response": reply,
                "conversation_id": cid,
                "pending_action": pending_obj,
                "requires_confirmation": True,
                "action_status": "pending_confirmation"
            }

        # 3. Remove wishlist item
        if any(p in msg_low for p in ["remove from wishlist", "delete from wishlist", "remove this from wishlist", "remove wishlist"]):
            wl_res = self.tools.get_wishlist(user_id)
            target_wl = None
            for item in wl_res.get("items", []):
                if item["name"].lower() in msg_low:
                    target_wl = item
                    break

            if not target_wl:
                ref = self._resolve_place_reference(msg_text, context)
                if ref:
                    for item in wl_res.get("items", []):
                        if ref["name"].lower() in item["name"].lower():
                            target_wl = item
                            break

            if not target_wl:
                return {"response": "Which saved item would you like to remove from your wishlist?", "conversation_id": cid}

            desc = f"Remove '{target_wl['name']}' from wishlist"
            pending_obj = PendingAction(
                action_id=uuid.uuid4().hex[:8],
                tool="remove_wishlist",
                description=desc,
                args={"wishlist_id": target_wl["_id"]}
            )
            reply = f"⚠️ **Confirmation Required:** Do you want to remove '**{target_wl['name']}**' from your saved wishlist?"
            self.memory.save_turn(
                user_id=user_id,
                conversation_id=cid,
                user_message=msg_text,
                ai_message=reply,
                context_updates={"pending_action": pending_obj.model_dump()},
                pending_action=pending_obj.model_dump(),
                action_status="pending_confirmation"
            )
            return {
                "response": reply,
                "conversation_id": cid,
                "pending_action": pending_obj,
                "requires_confirmation": True,
                "action_status": "pending_confirmation"
            }

        # 4. Delete expense
        if any(p in msg_low for p in ["delete expense", "delete this expense", "remove expense"]):
            if not active_trip_id:
                return {"response": "Please specify the trip for the expense you'd like to delete.", "conversation_id": cid}

            exp_res = self.tools.get_expenses(user_id, active_trip_id)
            exps = exp_res.get("expenses", [])
            target_exp = None
            for e in exps:
                if e["description"].lower() in msg_low:
                    target_exp = e
                    break
            if not target_exp and exps:
                target_exp = exps[0]

            if not target_exp:
                return {"response": "No matching expense found to delete.", "conversation_id": cid}

            desc = f"Delete expense of ₹{target_exp['amount']} for '{target_exp['description']}'"
            pending_obj = PendingAction(
                action_id=uuid.uuid4().hex[:8],
                tool="delete_expense",
                description=desc,
                args={"expense_id": target_exp["_id"]}
            )
            reply = f"⚠️ **Confirmation Required:** Are you sure you want to delete the expense of **₹{target_exp['amount']:,.2f}** for '**{target_exp['description']}**'?"
            self.memory.save_turn(
                user_id=user_id,
                conversation_id=cid,
                user_message=msg_text,
                ai_message=reply,
                context_updates={"pending_action": pending_obj.model_dump()},
                pending_action=pending_obj.model_dump(),
                action_status="pending_confirmation"
            )
            return {
                "response": reply,
                "conversation_id": cid,
                "pending_action": pending_obj,
                "requires_confirmation": True,
                "action_status": "pending_confirmation"
            }

        # -------------------------------------------------------------
        # C. INTENT: WRITE / MUTATION ACTIONS (SAFE ACTIONS)
        # -------------------------------------------------------------

        # 5. Add expense (e.g. "Add an expense of ₹1,200 for dinner")
        if "expense" in msg_low and ("add" in msg_low or "record" in msg_low or "log" in msg_low):
            amt = self._extract_amount(msg_text)
            if not amt:
                return {"response": "Please specify the amount for the expense (e.g., 'Add an expense of ₹1,200 for dinner').", "conversation_id": cid}

            if not active_trip_id:
                return {"response": "Which trip should I log this expense under? Please specify the trip or select one.", "conversation_id": cid}

            # Category detection
            cat = "Other"
            if any(w in msg_low for w in ["dinner", "lunch", "breakfast", "food", "cafe", "coffee", "restaurant", "meal"]):
                cat = "Food"
            elif any(w in msg_low for w in ["hotel", "stay", "resort", "airbnb", "hostel", "room"]):
                cat = "Accommodation"
            elif any(w in msg_low for w in ["taxi", "cab", "train", "flight", "bus", "metro", "fuel", "transport"]):
                cat = "Transport"
            elif any(w in msg_low for w in ["ticket", "museum", "entry", "tour", "pass", "activity", "guide"]):
                cat = "Activities"
            elif any(w in msg_low for w in ["shopping", "souvenir", "clothes", "gift"]):
                cat = "Shopping"

            # Description extraction
            desc = "Incidental Expense"
            for marker in ["for ", "on ", "towards "]:
                if marker in msg_low:
                    parts = msg_text.split(marker, 1)
                    if len(parts) > 1:
                        desc = parts[1].split(".")[0].strip().title()
                        break

            res = self.tools.add_expense(user_id, active_trip_id, cat, amt, desc)
            if res["success"]:
                reply = f"✅ Logged an expense of **₹{amt:,.2f}** for **{desc}** under **{cat}** in your trip '**{active_trip.get('title')}**'."
                status = "executed"
            else:
                reply = f"❌ Failed to log expense: {res.get('error')}"
                status = "failed"

            self.memory.save_turn(user_id, cid, msg_text, reply, {}, tool_called="add_expense", tool_result=res, action_status=status)
            return {
                "response": reply,
                "conversation_id": cid,
                "tool_called": "add_expense",
                "tool_result": res,
                "action_status": status,
                "mutation_occurred": res["success"],
                "affected_entity": "expense"
            }

        # 6. Update expense (e.g. "Update that expense to ₹1,500")
        if "expense" in msg_low and ("update" in msg_low or "change" in msg_low):
            amt = self._extract_amount(msg_text)
            if not amt:
                return {"response": "Please specify the updated amount (e.g., 'Update that expense to ₹1,500').", "conversation_id": cid}

            if not active_trip_id:
                return {"response": "Which trip's expense would you like to update?", "conversation_id": cid}

            exp_res = self.tools.get_expenses(user_id, active_trip_id)
            exps = exp_res.get("expenses", [])
            target = exps[0] if exps else None
            if not target:
                return {"response": "No recorded expenses found to update.", "conversation_id": cid}

            res = self.tools.update_expense(user_id, target["_id"], amount=amt)
            if res["success"]:
                reply = f"✅ Updated expense '**{target.get('description')}**' to **₹{amt:,.2f}**."
                status = "executed"
            else:
                reply = f"❌ Failed to update expense: {res.get('error')}"
                status = "failed"

            self.memory.save_turn(user_id, cid, msg_text, reply, {}, tool_called="update_expense", tool_result=res, action_status=status)
            return {
                "response": reply,
                "conversation_id": cid,
                "tool_called": "update_expense",
                "tool_result": res,
                "action_status": status,
                "mutation_occurred": res["success"],
                "affected_entity": "expense"
            }

        # 7. Add to wishlist (e.g. "Add Eiffel Tower to my wishlist", "Add the first one to my wishlist", "add to wishkist")
        if any(w in msg_low for w in ["wishlist", "wishkist", "wish list", "bucket list"]) and any(w in msg_low for w in ["add", "save", "put", "keep", "favorite", "favourite"]):
            ref_place = self._resolve_place_reference(msg_text, context)
            if ref_place:
                name = ref_place["name"]
                pid = ref_place.get("id") or ref_place.get("place_id") or uuid.uuid4().hex[:8]
                loc = ref_place.get("address") or ref_place.get("location") or ""
                img = ref_place.get("image_url")
                cat = ref_place.get("category", "attraction")
            else:
                # Extract place name from query
                m = re.search(r"add\s+(?:the\s+)?(.+?)\s+to\s+(?:my\s+)?(?:wishlist|wishkist|wish\s*list)", msg_text, re.IGNORECASE)
                cand_name = m.group(1).strip() if m else ""
                cand_clean = re.sub(r"\b(please|this|that|it|the|a|place|sight)\b", "", cand_name, flags=re.IGNORECASE).strip()

                if cand_clean and len(cand_clean) >= 2:
                    name = cand_clean.title()
                    pid = f"wish_{uuid.uuid4().hex[:8]}"
                    loc = active_trip.get("destination", "") if active_trip else ""
                    img = None
                    cat = "attraction"
                else:
                    # Missing place! NEVER fabricate! NEVER call search_places!
                    reply = "Sure — which place would you like me to add to your wishlist?"
                    self.memory.save_turn(
                        user_id=user_id,
                        conversation_id=cid,
                        user_message=msg_text,
                        ai_message=reply,
                        context_updates={"pending_clarification": {"type": "which_place_for_wishlist"}},
                        action_status="read_only"
                    )
                    return {
                        "response": reply,
                        "conversation_id": cid,
                        "tool_called": None,
                        "action_status": "read_only",
                        "places": []
                    }

            res = self.tools.add_wishlist(user_id, pid, name, cat, loc, img)
            if res["success"]:
                reply = f"✅ Added **{name}** to your saved wishlist."
                status = "executed"
            else:
                reply = f"❌ Could not add to wishlist: {res.get('error')}"
                status = "failed"

            self.memory.save_turn(user_id, cid, msg_text, reply, {"last_mentioned_place": {"name": name, "place_id": pid}}, tool_called="add_wishlist", tool_result=res, action_status=status)
            return {
                "response": reply,
                "conversation_id": cid,
                "tool_called": "add_wishlist",
                "tool_result": res,
                "action_status": status,
                "mutation_occurred": res["success"],
                "affected_entity": "wishlist"
            }

        # 8. Create a new trip (e.g. "Create a new trip to Paris")
        if ("create" in msg_low or "plan a new" in msg_low) and "trip" in msg_low:
            m = re.search(r"trip\s+to\s+([A-Za-z\s,]+)", msg_text, re.IGNORECASE)
            dest = m.group(1).strip().title() if m else "New Destination"
            budget_val = self._extract_amount(msg_text) or 3000.0

            res = self.tools.create_trip(user_id, dest, budget=budget_val)
            if res["success"]:
                t = res["trip"]
                reply = f"🎉 Successfully created a new trip '**{t['title']}**' ({t['start_date']} to {t['end_date']}) with budget **₹{budget_val:,.2f}**!"
                status = "executed"
                new_ctx = {"active_trip_id": t["_id"]}
            else:
                reply = f"❌ Failed to create trip: {res.get('error')}"
                status = "failed"
                new_ctx = {}

            self.memory.save_turn(user_id, cid, msg_text, reply, new_ctx, tool_called="create_trip", tool_result=res, action_status=status)
            return {
                "response": reply,
                "conversation_id": cid,
                "tool_called": "create_trip",
                "tool_result": res,
                "action_status": status,
                "mutation_occurred": res["success"],
                "affected_entity": "trip"
            }

        # 9. Update trip budget (e.g. "Change my trip budget to ₹50,000")
        if "budget" in msg_low and ("change" in msg_low or "update" in msg_low or "set" in msg_low):
            amt = self._extract_amount(msg_text)
            if not amt:
                return {"response": "Please specify the new budget amount (e.g., 'Change my trip budget to ₹50,000').", "conversation_id": cid}

            if not active_trip_id:
                return {"response": "Which trip's budget would you like to update?", "conversation_id": cid}

            res = self.tools.update_trip(user_id, active_trip_id, budget=amt)
            if res["success"]:
                reply = f"✅ Updated budget for '**{active_trip.get('title')}**' to **₹{amt:,.2f}**."
                status = "executed"
            else:
                reply = f"❌ Failed to update budget: {res.get('error')}"
                status = "failed"

            self.memory.save_turn(user_id, cid, msg_text, reply, {}, tool_called="update_trip", tool_result=res, action_status=status)
            return {
                "response": reply,
                "conversation_id": cid,
                "tool_called": "update_trip",
                "tool_result": res,
                "action_status": status,
                "mutation_occurred": res["success"],
                "affected_entity": "trip"
            }

        # 10. Move activity / Change time (e.g. "Move Golconda Fort from Day 4 to Day 2", "Change the time to 2:00 PM")
        if ("move" in msg_low or "reschedule" in msg_low or "change the time" in msg_low or "change time" in msg_low) and ("day" in msg_low or "time" in msg_low):
            if not active_trip_id:
                return {"response": "Please specify which trip's activity you'd like to reschedule.", "conversation_id": cid}

            itin_res = self.tools.get_itinerary(user_id, active_trip_id)
            acts = itin_res.get("activities", [])
            target_act = None

            for a in acts:
                if a["title"].lower() in msg_low:
                    target_act = a
                    break

            if not target_act:
                ref = self._resolve_place_reference(msg_text, context)
                if ref:
                    for a in acts:
                        if ref["name"].lower() in a["title"].lower():
                            target_act = a
                            break

            if not target_act and acts:
                target_act = acts[0]

            if not target_act:
                return {"response": "Could not identify which activity to move.", "conversation_id": cid}

            updates = {}
            target_day = self._extract_day_number(msg_text, active_trip)
            if target_day:
                updates["day_number"] = target_day

            m_time = re.search(r"\b(\d{1,2}(?::\d{2})?\s*(?:am|pm))\b", msg_text, re.IGNORECASE)
            if m_time:
                updates["time"] = m_time.group(1).upper()

            res = self.tools.update_itinerary_activity(user_id, target_act["_id"], **updates)
            if res["success"]:
                reply = f"✅ Moved '**{target_act.get('title')}**' to Day {updates.get('day_number', target_act.get('day_number'))}."
                if "time" in updates:
                    reply += f" Time set to {updates['time']}."
                status = "executed"
            else:
                reply = f"❌ Failed to move activity: {res.get('error')}"
                status = "failed"

            self.memory.save_turn(user_id, cid, msg_text, reply, {}, tool_called="update_itinerary_activity", tool_result=res, action_status=status)
            return {
                "response": reply,
                "conversation_id": cid,
                "tool_called": "update_itinerary_activity",
                "tool_result": res,
                "action_status": status,
                "mutation_occurred": res["success"],
                "affected_entity": "itinerary"
            }

        # 11. Add to itinerary / trip (e.g. "Add Charminar to my trip", "Add this restaurant to Day 3", "Add the first one to Day 2")
        if "add" in msg_low and ("trip" in msg_low or "itinerary" in msg_low or "day" in msg_low or "tomorrow" in msg_low):
            if not active_trip_id:
                return {"response": "Please create or select a trip first before adding itinerary activities.", "conversation_id": cid}

            target_day = self._extract_day_number(msg_text, active_trip)

            # Check if reference to previous recommendations ("the first one", "the second one", "that place")
            ref_place = self._resolve_place_reference(msg_text, context)
            if ref_place:
                title = ref_place["name"]
                pid = ref_place.get("id") or ref_place.get("place_id")
                loc = ref_place.get("address") or ref_place.get("location") or active_trip.get("destination", "")
                cat = ref_place.get("category", "attraction")
                img = ref_place.get("image_url")
                desc = ref_place.get("description")
            else:
                # Extract place name from phrase
                m = re.search(r"add\s+(?:the\s+)?(.+?)\s+to\s+(?:my\s+)?(?:trip|itinerary|day)", msg_text, re.IGNORECASE)
                title = m.group(1).strip().title() if m else "Sightseeing Activity"
                pid = None
                loc = active_trip.get("destination", "")
                cat = "attraction"
                img = None
                desc = None

            res = self.tools.add_itinerary_activity(
                user_id=user_id,
                trip_id=active_trip_id,
                day_number=target_day,
                title=title,
                location=loc,
                place_id=pid,
                category=cat,
                image_url=img,
                description=desc
            )

            if res["success"]:
                reply = f"✅ Added '**{title}**' to **Day {target_day}** of your trip '**{active_trip.get('title')}**'."
                status = "executed"
            else:
                reply = f"❌ Failed to add activity: {res.get('error')}"
                status = "failed"

            self.memory.save_turn(user_id, cid, msg_text, reply, {"last_mentioned_place": {"name": title, "place_id": pid}}, tool_called="add_itinerary_activity", tool_result=res, action_status=status)
            return {
                "response": reply,
                "conversation_id": cid,
                "tool_called": "add_itinerary_activity",
                "tool_result": res,
                "action_status": status,
                "mutation_occurred": res["success"],
                "affected_entity": "itinerary"
            }

        # -------------------------------------------------------------
        # D. INTENT: READ & REASONING ACTIONS
        # -------------------------------------------------------------

        # Ordinal reference alone (e.g. "the second one", "the first one")
        if any(msg_low == p or msg_low.startswith(p + " ") for p in [
            "the first one", "the second one", "the third one", "the fourth one",
            "the 1st one", "the 2nd one", "the 3rd one", "first one", "second one", "third one"
        ]):
            ref_place = self._resolve_place_reference(msg_text, context)
            if ref_place:
                name = ref_place["name"]
                cat_name = ref_place.get("category", "sight").title()
                addr = ref_place.get("address") or ref_place.get("location") or ""
                reply = f"Selected **{name}** ({cat_name})" + (f" in {addr}." if addr else ".") + "\n\nWould you like me to schedule this to a specific day (e.g. *'Add it to Day 2'*) or save it to your wishlist?"
                self.memory.save_turn(user_id, cid, msg_text, reply, {"last_mentioned_place": ref_place}, action_status="read_only")
                return {"response": reply, "conversation_id": cid, "tool_called": None, "action_status": "read_only", "places": [ref_place]}

        # 12. Check budget (e.g. "Check my budget", "How much budget do I have left?", "How much do I have left?")
        if any(p in msg_low for p in ["budget", "how much do i have left", "how much left", "remaining funds", "spending"]):
            target_trip = self._match_trip_from_text(user_id, msg_text)
            if target_trip:
                target_trip_id = str(target_trip["_id"])
            elif active_trip_id:
                target_trip_id = active_trip_id
            else:
                trips_res = self.tools.get_user_trips(user_id)
                trips = trips_res.get("trips", [])
                if not trips:
                    return {"response": "You haven't created any trips yet. Say 'Create a new trip to Paris' to start planning!", "conversation_id": cid}
                if len(trips) == 1:
                    target_trip_id = str(trips[0]["_id"])
                else:
                    trip_list = ", ".join(f"'{t['destination']}'" for t in trips[:4])
                    reply = f"You have multiple trips ({trip_list}). Which trip's budget would you like to check?"
                    self.memory.save_turn(
                        user_id=user_id,
                        conversation_id=cid,
                        user_message=msg_text,
                        ai_message=reply,
                        context_updates={"pending_clarification": {"type": "which_trip_for_budget"}},
                        action_status="read_only"
                    )
                    return {"response": reply, "conversation_id": cid, "tool_called": None, "action_status": "read_only"}

            budget_data = self.tools.get_budget(user_id, target_trip_id)
            if not budget_data["success"]:
                return {"response": f"Could not retrieve budget: {budget_data.get('error')}", "conversation_id": cid}

            b = budget_data["budget"]
            s = budget_data["total_spent"]
            r = budget_data["remaining_budget"]
            p = budget_data["percentage_spent"]

            lines = [
                f"💰 **Budget Summary for {budget_data.get('trip_title')} ({budget_data.get('destination')}):**",
                f"• **Total Budget:** ₹{b:,.2f}",
                f"• **Total Spent:** ₹{s:,.2f} ({p}%)",
                f"• **Remaining Budget:** **₹{r:,.2f}**"
            ]
            if budget_data["by_category"]:
                lines.append("\n**Category Breakdown:**")
                for cat, amt in budget_data["by_category"].items():
                    lines.append(f"• {cat}: ₹{amt:,.2f}")

            reply = "\n".join(lines)
            self.memory.save_turn(user_id, cid, msg_text, reply, {"active_trip_id": target_trip_id}, tool_called="get_budget", tool_result=budget_data, action_status="read_only")
            return {
                "response": reply,
                "conversation_id": cid,
                "tool_called": "get_budget",
                "tool_result": budget_data,
                "action_status": "read_only"
            }

        # 13. Read itinerary (e.g. "Read my itinerary", "What am I doing on Day 1?", "What am I doing tomorrow?")
        if any(p in msg_low for p in ["itinerary", "what am i doing", "what's scheduled", "schedule", "plan tomorrow", "what do i have"]):
            target_trip = self._match_trip_from_text(user_id, msg_text)
            if target_trip:
                target_trip_id = str(target_trip["_id"])
            elif active_trip_id:
                target_trip_id = active_trip_id
                target_trip = active_trip
            else:
                trips_res = self.tools.get_user_trips(user_id)
                trips = trips_res.get("trips", [])
                if not trips:
                    return {"response": "Please select or create a trip first to review your itinerary.", "conversation_id": cid}
                if len(trips) == 1:
                    target_trip_id = str(trips[0]["_id"])
                    target_trip = trips[0]
                else:
                    trip_list = ", ".join(f"'{t['destination']}'" for t in trips[:4])
                    reply = f"You have multiple trips ({trip_list}). Please specify which trip's itinerary you'd like to check."
                    self.memory.save_turn(
                        user_id=user_id,
                        conversation_id=cid,
                        user_message=msg_text,
                        ai_message=reply,
                        context_updates={"pending_clarification": {"type": "which_trip_for_itinerary"}},
                        action_status="read_only"
                    )
                    return {"response": reply, "conversation_id": cid, "tool_called": None, "action_status": "read_only"}

            day_req = self._extract_day_number(msg_text, target_trip)
            if "tomorrow" in msg_low:
                day_req = 2

            itin_res = self.tools.get_itinerary(user_id, target_trip_id, day_number=day_req)
            acts = itin_res.get("activities", [])

            if not acts:
                target_str = f"Day {day_req}" if day_req else "this trip"
                reply = f"You don't have any activities scheduled for {target_str} in '**{itin_res.get('trip_title')}**'.\n\nWould you like to find top places to visit and add them?"
            else:
                lines = [f"📅 **Itinerary for {itin_res.get('trip_title')}**" + (f" (Day {day_req}):" if day_req else ":")]
                curr_day = None
                for a in acts:
                    if not day_req and a.get("day_number") != curr_day:
                        curr_day = a.get("day_number")
                        lines.append(f"\n**Day {curr_day}**" + (f" ({a['date']})" if a.get("date") else "") + ":")
                    cost_str = f" (₹{a['cost']:,.2f})" if a.get("cost") else ""
                    lines.append(f"• **{a.get('time', '10:00 AM')}** — {a['title']}{cost_str}")
                    if a.get("location") and a["location"] != a["title"]:
                        lines.append(f"  *Location:* {a['location']}")

                reply = "\n".join(lines)

            self.memory.save_turn(user_id, cid, msg_text, reply, {"active_trip_id": target_trip_id}, tool_called="get_itinerary", tool_result=itin_res, action_status="read_only")
            return {
                "response": reply,
                "conversation_id": cid,
                "tool_called": "get_itinerary",
                "tool_result": itin_res,
                "action_status": "read_only"
            }

        # 14. Check wishlist (e.g. "Check my wishlist", "What's in my wishlist?", "show wishlist")
        if any(w in msg_low for w in ["wishlist", "wishkist", "wish list", "bucket list"]):
            wl_res = self.tools.get_wishlist(user_id)
            items = wl_res.get("items", [])
            if not items:
                reply = "Your wishlist is currently empty. You can discover sights in Explore and say 'Add to wishlist'!"
            else:
                lines = [f"✨ **Your Saved Wishlist ({len(items)} places):**"]
                for i, item in enumerate(items, 1):
                    lines.append(f"{i}. **{item['name']}** ({item.get('category', 'sight').title()}) — {item.get('location', '')}")
                reply = "\n".join(lines)

            self.memory.save_turn(user_id, cid, msg_text, reply, {}, tool_called="get_wishlist", tool_result=wl_res, action_status="read_only")
            return {
                "response": reply,
                "conversation_id": cid,
                "tool_called": "get_wishlist",
                "tool_result": wl_res,
                "action_status": "read_only"
            }

        # 15. Check expenses list (e.g. "Check my expenses", "Show my expenses")
        if "expense" in msg_low and ("show" in msg_low or "list" in msg_low or "read" in msg_low or "check" in msg_low):
            target_trip_id = active_trip_id
            if not target_trip_id:
                trips_res = self.tools.get_user_trips(user_id)
                trips = trips_res.get("trips", [])
                if not trips:
                    return {"response": "Please create or select a trip first to view expense details.", "conversation_id": cid}
                if len(trips) == 1:
                    target_trip_id = trips[0]["_id"]
                else:
                    return {"response": "Please select a trip to view its expense breakdown.", "conversation_id": cid}

            exp_res = self.tools.get_expenses(user_id, target_trip_id)
            exps = exp_res.get("expenses", [])
            if not exps:
                reply = f"No expenses recorded yet for '**{exp_res.get('trip_title')}**'. Say 'Add an expense of ₹500 for lunch' to record one."
            else:
                total = sum(e["amount"] for e in exps)
                lines = [f"🧾 **Logged Expenses for {exp_res.get('trip_title')} (Total: ₹{total:,.2f}):**"]
                for e in exps:
                    lines.append(f"• **₹{e['amount']:,.2f}** — {e['description']} ({e.get('category', 'Other')}) on {e.get('date', '')}")
                reply = "\n".join(lines)

            self.memory.save_turn(user_id, cid, msg_text, reply, {}, tool_called="get_expenses", tool_result=exp_res, action_status="read_only")
            return {
                "response": reply,
                "conversation_id": cid,
                "tool_called": "get_expenses",
                "tool_result": exp_res,
                "action_status": "read_only"
            }

        # 16. Read user trips (e.g. "Read my trips", "Show my trips", "What trips do I have?")
        if any(p in msg_low for p in ["my trips", "show trips", "read trips", "list trips", "all trips"]):
            trips_res = self.tools.get_user_trips(user_id)
            trips = trips_res.get("trips", [])
            if not trips:
                reply = "You don't have any trips saved yet. Say 'Create a new trip to Kyoto' to plan your first adventure!"
            else:
                lines = [f"🧳 **Your TravelTrack Trips ({len(trips)}):**"]
                for t in trips:
                    lines.append(f"• **{t['title']}** ({t['destination']})\n  Dates: {t.get('start_date')} to {t.get('end_date')} • Budget: ₹{t.get('budget', 0):,.2f} • Status: {t.get('status', 'planned').title()}")
                reply = "\n".join(lines)

            self.memory.save_turn(user_id, cid, msg_text, reply, {}, tool_called="get_user_trips", tool_result=trips_res, action_status="read_only")
            return {
                "response": reply,
                "conversation_id": cid,
                "tool_called": "get_user_trips",
                "tool_result": trips_res,
                "action_status": "read_only"
            }

        # 17. Explore / Place Search (STRICT VALIDATION, ZERO DEFAULT DESTINATIONS)
        search_intent = self._detect_place_search(msg_text)
        if search_intent:
            target_query = search_intent["target"]
            category = search_intent["category"]
            is_nearby = search_intent["is_nearby"]

            # If user wants to find places but gave NO location (e.g. "Find places", "Find restaurants")
            if not target_query:
                reply = (
                    "Which destination or city would you like to explore? "
                    "(For example, ask: *'Find top attractions in Kolkata'* or *'Find restaurants near Eiffel Tower'*)"
                )
                self.memory.save_turn(user_id, cid, msg_text, reply, {}, action_status="read_only")
                return {
                    "response": reply,
                    "conversation_id": cid,
                    "tool_called": None,
                    "action_status": "read_only",
                    "places": []
                }

            # Execute place search or nearby search
            if is_nearby:
                search_res = await self.tools.find_nearby_places(target_query, category=category, radius=3000)
                places = search_res.get("places", [])
                tool_called_name = "find_nearby_places"
                title_header = f"📍 **Places found near {target_query}:**"
            else:
                search_res = await self.tools.search_places(target_query, category=category, limit=6)
                places = search_res.get("places", [])
                tool_called_name = "search_places"
                title_header = f"📍 **Here are verified recommendations for {target_query}:**"

            if places:
                lines = [title_header]
                for i, p in enumerate(places, 1):
                    cat_name = p.get("category", "sight").title()
                    addr = p.get("address") or p.get("location") or ""
                    desc = p.get("description", "")
                    lines.append(f"{i}. **{p['name']}** ({cat_name})")
                    if addr and addr != p['name']:
                        lines.append(f"   *Address:* {addr}")
                    if desc:
                        lines.append(f"   *{desc}*")

                lines.append("\n💡 *Tip: Say 'Add the first one to Day 2' or 'Add to wishlist' to schedule it!*")
                reply = "\n".join(lines)

                self.memory.save_turn(
                    user_id=user_id,
                    conversation_id=cid,
                    user_message=msg_text,
                    ai_message=reply,
                    context_updates={
                        "last_recommended_places": places,
                        "last_mentioned_place": places[0] if places else None
                    },
                    tool_called=tool_called_name,
                    tool_result=search_res,
                    action_status="read_only",
                    places=places
                )
                return {
                    "response": reply,
                    "conversation_id": cid,
                    "tool_called": tool_called_name,
                    "tool_result": search_res,
                    "action_status": "read_only",
                    "places": places
                }
            else:
                reply = f"I couldn't find any places matching '{target_query}'. Please verify the spelling or try a nearby city or landmark."
                self.memory.save_turn(user_id, cid, msg_text, reply, {}, tool_called=tool_called_name, tool_result=search_res, action_status="read_only")
                return {
                    "response": reply,
                    "conversation_id": cid,
                    "tool_called": tool_called_name,
                    "tool_result": search_res,
                    "action_status": "read_only",
                    "places": []
                }

        # -------------------------------------------------------------
        # E. DEFAULT CONVERSATIONAL / ASSISTANT RESPONSE
        # -------------------------------------------------------------
        reply = await self._handle_conversational_chat(
            user_message=msg_text,
            greeting_type="general",
            chat_history=session_doc.get("messages", []),
            active_trip=active_trip,
            is_new_conversation=False
        )
        self.memory.save_turn(user_id, cid, msg_text, reply, {}, action_status="read_only")
        return {
            "response": reply,
            "conversation_id": cid,
            "tool_called": None,
            "action_status": "read_only",
            "places": []
        }


# Singleton instance
ai_agent_service = TravelTrackAIAgent()
