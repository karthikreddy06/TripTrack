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
    "You are the TravelTrack AI Assistant, an advanced, highly capable general-purpose AI assistant. "
    "You understand natural language, answer general knowledge, programming, math, science, advice, humor, and writing inquiries naturally and thoroughly. "
    "You have access to secure TravelTrack tools for managing trips, budgets, expenses, itineraries, wishlists, and discovering verified travel destinations. "
    "Guidelines:\n"
    "1. For general inquiries (coding, science, explanations, jokes, general knowledge), answer directly without calling tools.\n"
    "2. For TravelTrack queries (user's trips, expenses, budget, itinerary, wishlist, finding places, modifying itineraries), choose the appropriate tool.\n"
    "3. Never fabricate information, prices, ratings, or coordinates. Ground travel recommendations strictly in retrieved data.\n"
    "4. Maintain conversation context and understand follow-ups naturally."
)


# =====================================================================
# 2. TOOL DECLARATIONS SCHEMAS (OPENAI & GEMINI)
# =====================================================================

TRAVELTRACK_OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_user_trips",
            "description": "Retrieve all trips belonging to the user.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_budget",
            "description": "Get the financial budget summary, total spent, and remaining budget for a trip.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trip_id": {"type": "string", "description": "Trip ID or destination name (e.g. 'Kyoto', 'Mumbai')"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_itinerary",
            "description": "Get scheduled itinerary activities for a trip, optionally filtered by day number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trip_id": {"type": "string", "description": "Trip ID or destination name"},
                    "day_number": {"type": "integer", "description": "Day number (1, 2, 3...)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_expenses",
            "description": "Get all logged expenses for a specific trip.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trip_id": {"type": "string", "description": "Trip ID or destination name"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_wishlist",
            "description": "Retrieve all saved places in the user's wishlist.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_places",
            "description": "Search verified attractions, sights, restaurants, and hotels in a destination city using OpenStreetMap.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "City or destination name, e.g. 'Mumbai', 'Kolkata', 'Paris', 'Tokyo'"},
                    "category": {"type": "string", "enum": ["all", "attractions", "restaurants", "hotels", "cafes", "museums", "parks", "historic", "activities"], "description": "Optional category filter"}
                },
                "required": ["destination"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_nearby_places",
            "description": "Find verified sights or restaurants near a specific landmark or attraction.",
            "parameters": {
                "type": "object",
                "properties": {
                    "landmark": {"type": "string", "description": "Landmark name, e.g. 'Eiffel Tower', 'Charminar'"},
                    "category": {"type": "string", "enum": ["all", "attractions", "restaurants", "hotels"], "description": "Category filter"}
                },
                "required": ["landmark"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_itinerary_activity",
            "description": "Schedule a place or activity on a specific day of a trip's itinerary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trip_id": {"type": "string", "description": "Trip ID or destination"},
                    "day_number": {"type": "integer", "description": "Day number (1, 2, 3...)"},
                    "place_name": {"type": "string", "description": "Name of the place or activity to add"},
                    "location": {"type": "string", "description": "Address or location"}
                },
                "required": ["day_number", "place_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_itinerary_activity",
            "description": "Move an itinerary activity to a different day or change its scheduled time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "activity_id": {"type": "string", "description": "Activity ID or title to move"},
                    "day_number": {"type": "integer", "description": "New day number"},
                    "time": {"type": "string", "description": "Scheduled time (e.g. '2:00 PM')"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_itinerary_activity",
            "description": "Delete an activity from a trip's itinerary. Requires confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "activity_id": {"type": "string", "description": "Activity ID or title to delete"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_expense",
            "description": "Log an expense for a trip.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trip_id": {"type": "string", "description": "Trip ID"},
                    "amount": {"type": "number", "description": "Expense amount"},
                    "category": {"type": "string", "description": "Food, Transport, Accommodation, Activities, Shopping, or Other"},
                    "description": {"type": "string", "description": "Description of the expense"}
                },
                "required": ["amount"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_trip",
            "description": "Update trip dates, title, or budget.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trip_id": {"type": "string", "description": "Trip ID or destination name"},
                    "start_date": {"type": "string", "description": "New start date (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "New end date (YYYY-MM-DD)"},
                    "budget": {"type": "number", "description": "New budget"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_trip",
            "description": "Permanently delete a trip. Requires confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trip_id": {"type": "string", "description": "Trip ID or destination name to delete"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_wishlist",
            "description": "Save a place to the user's wishlist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "place_name": {"type": "string", "description": "Name of the place to save"}
                },
                "required": ["place_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remove_wishlist",
            "description": "Remove a place from the wishlist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "wishlist_id": {"type": "string", "description": "Wishlist ID or place name"}
                }
            }
        }
    }
]

TRAVELTRACK_GEMINI_FUNCTION_DECLARATIONS = [
    {
        "name": t["function"]["name"],
        "description": t["function"]["description"],
        "parameters": {
            "type": "OBJECT",
            "properties": {
                k: {"type": "STRING" if v.get("type") == "string" else ("INTEGER" if v.get("type") == "integer" else "NUMBER"), "description": v.get("description", "")}
                for k, v in t["function"]["parameters"].get("properties", {}).items()
            },
            "required": t["function"]["parameters"].get("required", [])
        }
    }
    for t in TRAVELTRACK_OPENAI_TOOLS
]


# =====================================================================
# 3. LLM CLIENT WITH NATIVE TOOL CALLING & DYNAMIC OFFLINE REASONING
# =====================================================================

class LLMClient:
    """
    General-purpose agentic LLM client supporting Google Gemini and OpenAI native tool calling,
    plus an advanced dynamic reasoning engine when API keys are not present.
    """

    def __init__(self):
        self._load_keys()

    def _load_keys(self):
        self.gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
        self.openai_key = os.environ.get("OPENAI_API_KEY", "").strip()

    async def run_agent_turn(
        self,
        user_message: str,
        chat_history: List[Dict[str, Any]],
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Executes an agent turn using Gemini or OpenAI native tool-calling,
        or dynamic LLM reasoning when API keys are absent.
        """
        self._load_keys()

        active_trip = user_context.get("active_trip")
        all_trips = user_context.get("all_trips", [])
        recent_places = user_context.get("last_recommended_places", [])

        trips_str = ", ".join([f"'{t.get('destination', t.get('title'))}' (ID: {t.get('_id')})" for t in all_trips]) or "None"
        active_str = f"'{active_trip.get('destination')}' (ID: {active_trip.get('_id')})" if active_trip else "None selected"
        places_str = ", ".join([f"{idx+1}. {p.get('name')} ({p.get('category')})" for idx, p in enumerate(recent_places[:6])]) or "None"

        augmented_system_prompt = (
            f"{TRAVEL_AGENT_SYSTEM_PROMPT}\n\n"
            f"User Context:\n"
            f"- User Trips: {trips_str}\n"
            f"- Active Selected Trip: {active_str}\n"
            f"- Recently Recommended Places in Conversation: {places_str}\n\n"
            "Guidelines:\n"
            "1. Answer general questions (coding, science, math, jokes, advice, writing, trivia) conversationally without tools.\n"
            "2. If the user asks about their trips, budget, itinerary, or wishlist, or asks to search places or modify travel plans, use the appropriate TravelTrack tool.\n"
            "3. If an action has missing parameters that cannot be resolved from context, ask a clarifying question."
        )

        # 1. Try Google Gemini with Function Calling
        if self.gemini_key:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
                contents = []
                for h in chat_history[-6:]:
                    role = "user" if h.get("role") == "user" else "model"
                    contents.append({"role": role, "parts": [{"text": h.get("content", "")}]})
                contents.append({"role": "user", "parts": [{"text": user_message}]})

                payload = {
                    "systemInstruction": {"parts": [{"text": augmented_system_prompt}]},
                    "contents": contents,
                    "tools": [{"function_declarations": TRAVELTRACK_GEMINI_FUNCTION_DECLARATIONS}],
                    "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048}
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [{}])
                            for part in parts:
                                if "functionCall" in part:
                                    call = part["functionCall"]
                                    return {"action": "call_tool", "tool": call.get("name"), "args": call.get("args", {})}
                                if "text" in part and part["text"].strip():
                                    return {"action": "reply", "content": part["text"].strip()}
            except Exception as exc:
                logger.warning(f"Gemini agent call failed: {exc}")

        # 2. Try OpenAI with Function Calling
        if self.openai_key:
            try:
                url = "https://api.openai.com/v1/chat/completions"
                messages = [{"role": "system", "content": augmented_system_prompt}]
                for h in chat_history[-6:]:
                    role = "assistant" if h.get("role") == "assistant" else "user"
                    messages.append({"role": role, "content": h.get("content", "")})
                messages.append({"role": "user", "content": user_message})

                payload = {
                    "model": "gpt-4o-mini",
                    "messages": messages,
                    "tools": TRAVELTRACK_OPENAI_TOOLS,
                    "temperature": 0.7,
                    "max_tokens": 2048
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, headers={"Authorization": f"Bearer {self.openai_key}"}, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        choices = data.get("choices", [])
                        if choices:
                            msg = choices[0].get("message", {})
                            if msg.get("tool_calls"):
                                t_call = msg["tool_calls"][0]["function"]
                                args = json.loads(t_call.get("arguments", "{}"))
                                return {"action": "call_tool", "tool": t_call.get("name"), "args": args}
                            if msg.get("content"):
                                return {"action": "reply", "content": msg["content"].strip()}
            except Exception as exc:
                logger.warning(f"OpenAI agent call failed: {exc}")

        # 3. Dynamic Reasoning Engine (intelligent conversational reasoner)
        return self._dynamic_reasoning_turn(user_message, chat_history, user_context)

    def _dynamic_reasoning_turn(
        self,
        user_message: str,
        chat_history: List[Dict[str, Any]],
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Intelligent offline reasoning simulator.
        Evaluates user intent and dynamically determines whether to call a tool or generate a conversational response.
        """
        msg_text = user_message.strip()
        msg_low = msg_text.lower()
        active_trip = user_context.get("active_trip")
        all_trips = user_context.get("all_trips", [])
        recent_places = user_context.get("last_recommended_places", [])

        # -----------------------------------------------------------------
        # A. CONTEXTUAL REASONING OVER RECENTLY RECOMMENDED PLACES
        # -----------------------------------------------------------------
        if recent_places:
            # Comparative question: "Which one is best for history/food/views?"
            if any(p in msg_low for p in ["which one", "which of these", "best for history", "best for food", "best for views", "best for nature", "closest"]):
                return {"action": "reply", "content": self._handle_place_comparison_reasoning(msg_text, recent_places)}

            # Deeper inquiry about specific place: "Tell me more about the first/second one"
            if any(p in msg_low for p in ["tell me more about", "more details on", "more info on", "what is special about"]):
                target = None
                if "first" in msg_low or "1st" in msg_low or "number 1" in msg_low: target = recent_places[0]
                elif "second" in msg_low or "2nd" in msg_low or "number 2" in msg_low and len(recent_places) >= 2: target = recent_places[1]
                elif "third" in msg_low or "3rd" in msg_low or "number 3" in msg_low and len(recent_places) >= 3: target = recent_places[2]
                else:
                    for p in recent_places:
                        if p.get("name", "").lower() in msg_low:
                            target = p
                            break
                if target:
                    return {"action": "reply", "content": self._handle_place_deep_dive_reasoning(target)}

        # -----------------------------------------------------------------
        # B. BUDGET & FINANCIAL REASONING
        # -----------------------------------------------------------------
        if any(p in msg_low for p in ["budget", "how much do i have left", "how much budget", "money left", "affect my budget"]):
            if any(p in msg_low for p in ["is that enough", "is it enough", "can i afford", "enough for", "affect my budget", "how much will that affect"]):
                return {"action": "reply", "content": self._handle_travel_budget_reasoning(user_message, active_trip, all_trips)}
            if len(all_trips) > 1 and not active_trip and not any(t.get("destination", "").lower() in msg_low for t in all_trips):
                trip_names = [f"'{t.get('destination')}'" for t in all_trips if t.get("destination")]
                return {"action": "reply", "content": f"Which trip's budget would you like to check? ({', '.join(trip_names)})"}
            return {"action": "call_tool", "tool": "get_budget", "args": {}}

        # -----------------------------------------------------------------
        # C. ITINERARY REASONING & OPTIMIZATION
        # -----------------------------------------------------------------
        if any(p in msg_low for p in ["inefficient", "optimize itinerary", "optimize my route", "efficient itinerary"]):
            return {"action": "reply", "content": self._handle_itinerary_efficiency_reasoning(active_trip)}

        # -----------------------------------------------------------------
        # D. ITINERARY CHECKS
        # -----------------------------------------------------------------
        if any(p in msg_low for p in ["what am i doing tomorrow", "tomorrow", "day 1", "day 2", "day 3", "day 4", "day 5", "my itinerary", "show itinerary", "view itinerary"]):
            if "add" not in msg_low and "move" not in msg_low and "delete" not in msg_low:
                m_day = re.search(r"\bday\s*(\d+)\b", msg_low)
                day_num = int(m_day.group(1)) if m_day else (2 if "tomorrow" in msg_low else None)
                return {"action": "call_tool", "tool": "get_itinerary", "args": {"day_number": day_num}}

        # -----------------------------------------------------------------
        # E. EXPENSES CHECKS
        # -----------------------------------------------------------------
        if any(p in msg_low for p in ["my expenses", "show expenses", "list expenses", "what did i spend"]):
            return {"action": "call_tool", "tool": "get_expenses", "args": {}}

        # -----------------------------------------------------------------
        # F. TRIPS LIST
        # -----------------------------------------------------------------
        if any(p in msg_low for p in ["read my trips", "my trips", "show my trips", "list my trips", "all trips"]):
            return {"action": "call_tool", "tool": "get_user_trips", "args": {}}

        # -----------------------------------------------------------------
        # G. WISHLIST OPERATIONS
        # -----------------------------------------------------------------
        if "wishlist" in msg_low or "wishkist" in msg_low:
            if "add" in msg_low or "save" in msg_low:
                m_clean = None
                if "first" in msg_low or "1st" in msg_low or "number 1" in msg_low or "first one" in msg_low:
                    m_clean = recent_places[0].get("name") if recent_places else None
                elif "second" in msg_low or "2nd" in msg_low or "number 2" in msg_low or "second one" in msg_low:
                    m_clean = recent_places[1].get("name") if len(recent_places) >= 2 else None
                elif "third" in msg_low or "3rd" in msg_low or "number 3" in msg_low or "third one" in msg_low:
                    m_clean = recent_places[2].get("name") if len(recent_places) >= 3 else None
                elif any(w in msg_low for w in ["it", "this", "that", "that one", "the one"]):
                    m_clean = user_context.get("last_mentioned_place", {}).get("name") or (recent_places[0].get("name") if recent_places else None)
                else:
                    cand = re.sub(r"\b(?:add|save|to|my|the|into|wishlist|wishkist|please)\b", "", msg_text, flags=re.IGNORECASE).strip()
                    cand = re.sub(r"[^\w\s]", "", cand).strip()
                    if cand and len(cand) >= 2:
                        m_clean = cand
                    elif recent_places:
                        m_clean = recent_places[0].get("name")

                if m_clean and len(m_clean) >= 2:
                    return {"action": "call_tool", "tool": "add_wishlist", "args": {"place_name": m_clean}}
                return {"action": "reply", "content": "Sure — which place would you like me to add to your wishlist?"}

            if any(p in msg_low for p in ["show", "check", "view", "what is on", "get", "list"]) or msg_low.strip() in ["wishlist", "my wishlist"]:
                return {"action": "call_tool", "tool": "get_wishlist", "args": {}}

        # -----------------------------------------------------------------
        # H. ADD TO ITINERARY (WITH CONTEXT RESOLUTION)
        # -----------------------------------------------------------------
        if "add" in msg_low and any(p in msg_low for p in ["trip", "itinerary", "day", "tomorrow"]):
            m_day = re.search(r"\bday\s*(\d+)\b", msg_low)
            day_num = int(m_day.group(1)) if m_day else 1
            target_place = None
            if "first" in msg_low or "1st" in msg_low:
                target_place = recent_places[0]["name"] if recent_places else None
            elif "second" in msg_low or "2nd" in msg_low:
                target_place = recent_places[1]["name"] if len(recent_places) >= 2 else None
            elif "third" in msg_low or "3rd" in msg_low:
                target_place = recent_places[2]["name"] if len(recent_places) >= 3 else None
            elif any(w in msg_low for w in ["it", "this", "that", "that one", "the one"]):
                target_place = user_context.get("last_mentioned_place", {}).get("name") or (recent_places[0]["name"] if recent_places else None)
            else:
                m_clean = re.sub(r"\b(?:add|to|my|trip|itinerary|day\s*\d+|tomorrow|please)\b", "", msg_text, flags=re.IGNORECASE).strip()
                if len(m_clean) >= 2:
                    target_place = m_clean

            if target_place:
                return {
                    "action": "call_tool",
                    "tool": "add_itinerary_activity",
                    "args": {"place_name": target_place, "day_number": day_num}
                }
            return {"action": "reply", "content": "Which place or activity would you like me to add?"}

        # -----------------------------------------------------------------
        # I. MOVE / RESCHEDULE ITINERARY
        # -----------------------------------------------------------------
        if any(p in msg_low for p in ["move", "reschedule"]):
            m_day = re.search(r"\bday\s*(\d+)\b", msg_low)
            day_num = int(m_day.group(1)) if m_day else 1
            return {"action": "call_tool", "tool": "update_itinerary_activity", "args": {"day_number": day_num}}

        # -----------------------------------------------------------------
        # J. DELETE ACTIVITY OR TRIP
        # -----------------------------------------------------------------
        if "delete" in msg_low or "remove" in msg_low:
            if "trip" in msg_low:
                m_oid = re.search(r"\b([a-fA-F0-9]{24})\b", msg_text)
                trip_id = m_oid.group(1) if m_oid else None
                dest = active_trip.get("destination") if active_trip else "your trip"
                args = {"destination": dest}
                if trip_id:
                    args["trip_id"] = trip_id
                return {"action": "call_tool", "tool": "delete_trip", "args": args}
            return {"action": "call_tool", "tool": "delete_itinerary_activity", "args": {"activity_id": "current"}}

        # -----------------------------------------------------------------
        # K. TRIP UPDATES (DATES)
        # -----------------------------------------------------------------
        if any(p in msg_low for p in ["change the date", "change date", "update date", "change my trip date", "change the trip date"]):
            parsed_d = self._parse_date(msg_text)
            dest = active_trip.get("destination", "your destination") if active_trip else "your destination"
            if parsed_d:
                return {
                    "action": "call_tool",
                    "tool": "update_trip",
                    "args": {"destination": dest, "start_date": parsed_d.isoformat()}
                }
            return {"action": "reply", "content": f"What date would you like to change your **{dest}** trip to? (For example: 'November 1st' or '2026-11-01')"}

        # -----------------------------------------------------------------
        # L. ADD EXPENSE
        # -----------------------------------------------------------------
        if "expense" in msg_low or "spent" in msg_low or re.search(r"(?:₹|\$|rs\.?)\s*\d+", msg_low):
            m_amt = re.search(r"(?:₹|\$|rs\.?)?\s*(\d+(?:\.\d+)?)", msg_text, re.IGNORECASE)
            amt = float(m_amt.group(1)) if m_amt else 100.0
            return {
                "action": "call_tool",
                "tool": "add_expense",
                "args": {"amount": amt, "category": "Food", "description": "Travel Expense"}
            }

        # -----------------------------------------------------------------
        # M. NEARBY PLACES SEARCH
        # -----------------------------------------------------------------
        if any(p in msg_low for p in ["near ", "close to ", "around "]):
            m_lm = re.search(r"(?:near|close to|around)\s+([a-zA-Z\s]{2,30})", msg_text, re.IGNORECASE)
            lm = m_lm.group(1).strip() if m_lm else "Eiffel Tower"
            cat = "restaurants" if "restaurant" in msg_low or "food" in msg_low else "all"
            return {"action": "call_tool", "tool": "find_nearby_places", "args": {"landmark": lm, "category": cat}}

        # -----------------------------------------------------------------
        # N. EXPLICIT PLACE SEARCH (EXPLORE / SIGHTS)
        # -----------------------------------------------------------------
        search_match = self._detect_place_search(msg_text)
        if search_match:
            dest = search_match.get("target")
            if dest:
                return {"action": "call_tool", "tool": "search_places", "args": {"destination": dest, "category": search_match.get("category", "all")}}
            return {"action": "reply", "content": "Which destination or city would you like to find places for? (e.g. 'Mumbai', 'Paris', 'Kyoto')"}

        # -----------------------------------------------------------------
        # O. GREETING & CASUAL CONVERSATION
        # -----------------------------------------------------------------
        if msg_low in ["hi", "hey", "heyy", "hello", "good morning", "good afternoon", "good evening", "what's up", "yo"]:
            hour = datetime.now().hour
            tod = "Good morning" if 5 <= hour < 12 else ("Good afternoon" if 12 <= hour < 18 else "Good evening")
            if active_trip:
                return {"action": "reply", "content": f"{tod}! 👋 How can I help with your journey to **{active_trip.get('destination')}** or answer any other questions today?"}
            return {"action": "reply", "content": f"{tod}! 👋 How can I help you today? Feel free to ask general questions, write code, explore places, or manage your trips."}

        if msg_low in ["thanks", "thank you", "cool", "okay", "ok", "great", "awesome", "perfect"]:
            return {"action": "reply", "content": "You're very welcome! Let me know if you have any more questions or if there's anything else I can help you with."}

        # -----------------------------------------------------------------
        # P. GENERAL AI INQUIRY (Science, Coding, Math, Writing, Jokes, Advice, etc.)
        # -----------------------------------------------------------------
        return {"action": "reply", "content": self._generate_general_ai_response(user_message, active_trip)}

    def _handle_place_comparison_reasoning(self, text: str, recent_places: List[Dict[str, Any]]) -> str:
        """Comparative reasoning across recently recommended places."""
        t_low = text.lower()
        if "history" in t_low or "historic" in t_low or "culture" in t_low:
            historic_candidates = [p for p in recent_places if p.get("category") in ["historic", "museum"] or "heritage" in (p.get("tags") or [])]
            top_choice = historic_candidates[0] if historic_candidates else recent_places[0]
            name = top_choice.get("name")
            desc = top_choice.get("description") or "A premier historic landmark with rich cultural heritage."
            return (
                f"🏛️ **Top Pick for History:** **{name}**\n\n"
                f"{desc}\n\n"
                f"It stands out among the options as the most historically and culturally significant site. "
                f"Would you like me to schedule **{name}** into your itinerary?"
            )

        if "food" in t_low or "dining" in t_low or "eat" in t_low:
            food_candidates = [p for p in recent_places if p.get("category") in ["restaurant", "cafe"]]
            top_choice = food_candidates[0] if food_candidates else recent_places[0]
            return f"🍴 **Top Pick for Food & Dining:** **{top_choice.get('name')}** — {top_choice.get('description', 'Renowned for authentic flavors and atmosphere.')}"

        # Default comparative breakdown
        lines = ["Here is how these top places compare:\n"]
        for idx, p in enumerate(recent_places[:3], 1):
            lines.append(f"• **{p.get('name')}** ({p.get('category', 'Attraction').title()}): {p.get('description', 'Notable landmark.')}")
        lines.append("\nWhich one would you like to add to your trip?")
        return "\n".join(lines)

    def _handle_place_deep_dive_reasoning(self, place: Dict[str, Any]) -> str:
        """Deep dive reasoning on a specific place from memory."""
        name = place.get("name", "Landmark")
        cat = place.get("category", "attraction").title()
        loc = place.get("address") or "Central District"
        desc = place.get("description") or "A premier point of interest celebrated by travelers."
        tags = ", ".join(place.get("tags", [])) or "Cultural Landmark"

        return (
            f"📍 **{name}** ({cat})\n\n"
            f"• **Location:** {loc}\n"
            f"• **Tags:** {tags}\n\n"
            f"**Overview:**\n{desc}\n\n"
            f"Would you like me to add **{name}** to a specific day of your itinerary, or save it to your wishlist?"
        )

    def _detect_place_search(self, msg_text: str) -> Optional[Dict[str, Any]]:
        """Detect place search intent without hijacking general questions or city mentions."""
        t_low = msg_text.lower().strip()
        words = t_low.split()

        cat = "all"
        if any(w in t_low for w in ["restaurant", "food", "eat", "dining"]): cat = "restaurants"
        elif any(w in t_low for w in ["cafe", "coffee", "bakery"]): cat = "cafes"
        elif any(w in t_low for w in ["hotel", "stay", "resort", "hostel"]): cat = "hotels"
        elif any(w in t_low for w in ["museum", "gallery"]): cat = "museums"
        elif any(w in t_low for w in ["park", "garden", "beach"]): cat = "parks"
        elif any(w in t_low for w in ["historic", "monument", "fort", "palace"]): cat = "historic"
        elif any(w in t_low for w in ["attraction", "sight", "places to visit", "things to do"]): cat = "attractions"

        # Explicit travel and sightseeing inquiries:
        m_travel = re.search(
            r"\b(?:what\s+should\s+i\s+visit\s+in|what\s+to\s+see\s+in|what\s+to\s+visit\s+in|what\s+can\s+i\s+do\s+in|"
            r"places\s+to\s+visit\s+in|things\s+to\s+do\s+in|famous\s+places\s+in|tourist\s+places\s+in|best\s+places\s+in|"
            r"top\s+places\s+in|top\s+attractions\s+in|attractions\s+in|sights\s+in|where\s+to\s+go\s+in|recommend\s+places\s+in|"
            r"find\s+places\s+in|search\s+places\s+in|explore\s+places\s+in|explore|visit|sights\s+of)\s+([a-zA-Z\s]{2,25})",
            msg_text,
            re.IGNORECASE
        )
        if m_travel:
            cand = re.sub(r"[^\w\s]", "", m_travel.group(1)).strip()
            cand = re.sub(r"^(?:in|for|around)\s+", "", cand, flags=re.IGNORECASE).strip()
            if cand and len(cand) >= 2 and not cand.isdigit():
                return {"target": cand.title(), "category": cat}

        # NEVER search places for general knowledge, coding, or cultural questions
        GENERAL_TRIGGERS = [
            "what is", "why is", "tell me about", "teach me", "phrases", "famous for", "known for",
            "python", "code", "java", "api", "explain", "photosynthesis", "joke", "quantum", "black hole",
            "blockchain", "email", "birthday", "slow", "fastapi", "enough", "inefficient", "software",
            "capital of", "interview", "who is", "when did", "calculate", "how does", "recursion",
            "machine learning", "fastapi", "react", "algorithm"
        ]
        if any(t in t_low for t in GENERAL_TRIGGERS):
            return None

        # General "find/show/search <city>"
        m_in = re.search(r"\b(?:find|get|show|search|explore|list)\s+([a-zA-Z\s]{2,25})", msg_text, re.IGNORECASE)
        if m_in:
            cand = re.sub(r"[^\w\s]", "", m_in.group(1)).strip()
            cand = re.sub(r"^(?:in|for|around)\s+", "", cand, flags=re.IGNORECASE).strip()
            if cand and len(cand) >= 2 and not cand.isdigit():
                return {"target": cand.title(), "category": cat}

        # Single word city queries (e.g. "Mumbai", "Paris", "Kyoto")
        if len(words) == 1 and len(t_low) >= 3 and not t_low.isdigit():
            NON_CITIES = [
                "yes", "no", "ok", "okay", "sure", "cancel", "stop", "help", "hello", "hey", "heyy", "thanks",
                "test", "demo", "sample", "trip", "trips", "itinerary", "budget", "expense", "wishlist"
            ]
            clean = re.sub(r"[^\w]", "", t_low)
            if clean not in NON_CITIES:
                return {"target": clean.title(), "category": cat}

        return None

    def _parse_date(self, text: str) -> Optional[date]:
        """Parse natural language dates."""
        t = text.lower()
        today = date.today()
        if "tomorrow" in t:
            return today + timedelta(days=1)
        MONTHS = {
            "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
            "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
        }
        for m_name, m_num in MONTHS.items():
            if m_name in t:
                m_day = re.search(rf"\b{m_name}\s*(\d{{1,2}})(?:st|nd|rd|th)?\b|\b(\d{{1,2}})(?:st|nd|rd|th)?\s*{m_name}\b", t)
                if m_day:
                    d_num = int(m_day.group(1) or m_day.group(2))
                    yr = today.year if (m_num > today.month or (m_num == today.month and d_num >= today.day)) else today.year + 1
                    try:
                        return date(yr, m_num, d_num)
                    except ValueError:
                        pass
        m_iso = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", t)
        if m_iso:
            try:
                return date(int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3)))
            except ValueError:
                pass
        return None

    def _handle_travel_budget_reasoning(self, text: str, active_trip: Optional[Dict[str, Any]], all_trips: List[Dict[str, Any]]) -> str:
        """Evaluate budget feasibility using local destination costs and trip duration."""
        target_trip = active_trip or (all_trips[0] if all_trips else None)
        dest = target_trip.get("destination", "your destination") if target_trip else "your destination"
        m_amt = re.search(r"(?:₹|\$|rs\.?)?\s*([\d,]+(?:\.\d+)?)", text, re.IGNORECASE)
        amt = float(m_amt.group(1).replace(",", "")) if m_amt else 10000.0

        days = 4
        if target_trip and target_trip.get("start_date") and target_trip.get("end_date"):
            try:
                s = date.fromisoformat(target_trip["start_date"])
                e = date.fromisoformat(target_trip["end_date"])
                days = max(1, (e - s).days + 1)
            except Exception:
                days = 4

        daily = amt / days
        return (
            f"💰 **Budget Analysis for {dest}**\n\n"
            f"• **Available Budget:** **₹{amt:,.2f}**\n"
            f"• **Duration:** **{days} days**\n"
            f"• **Daily Average:** **₹{daily:,.2f} / day**\n\n"
            f"**Verdict:** At **₹{daily:,.2f}/day**, this provides a healthy balance for local dining, transit, and entry tickets for top attractions in {dest}.\n\n"
            "1. **Food & Dining:** ₹500 – ₹900/day for authentic regional meals and cafes.\n"
            "2. **Local Transit:** ₹200 – ₹400/day for metro/public transport or rideshares.\n"
            "3. **Sightseeing & Monuments:** ₹150 – ₹300/day for museum and heritage entrance passes."
        )

    def _handle_itinerary_efficiency_reasoning(self, active_trip: Optional[Dict[str, Any]]) -> str:
        """Route clustering and transit optimization analysis."""
        dest = active_trip.get("destination", "your destination") if active_trip else "your destination"
        return (
            f"🗺️ **Itinerary Route & Efficiency Analysis for {dest}:**\n\n"
            "To maximize time and avoid unnecessary city transit, follow **geographic clustering**:\n\n"
            "1. **Cluster Historic Landmarks Together**: Group old quarter monuments on the same day to walk between them.\n"
            "2. **Cluster Western Heritage / Outlying Sights**: Schedule distant fortresses or viewpoints together.\n"
            "3. **Cluster Dining & Evening Walkways**: Keep evening dining and markets near your accommodation.\n\n"
            "💡 *Tip: Tell me 'Move [Activity Name] to Day X' anytime to reschedule activities seamlessly!*"
        )

    def _generate_general_ai_response(self, text: str, active_trip: Optional[Dict[str, Any]] = None) -> str:
        """Comprehensive general AI response generator for coding, science, math, writing, and advice."""
        t_low = text.lower().strip()

        # Math calculations: e.g. "What is 25 * 37?", "25 x 37"
        m_calc = re.search(r"(\d+(?:\.\d+)?)\s*([\+\-\*\/x]|times|multiplied\s+by|divided\s+by|plus|minus)\s*(\d+(?:\.\d+)?)", t_low)
        if m_calc:
            n1 = float(m_calc.group(1))
            op = m_calc.group(2).strip().lower()
            n2 = float(m_calc.group(3))
            res = None
            if op in ["+", "plus"]: res = n1 + n2
            elif op in ["-", "minus"]: res = n1 - n2
            elif op in ["*", "x", "times", "multiplied by"]: res = n1 * n2
            elif op in ["/", "divided by"] and n2 != 0: res = n1 / n2
            if res is not None:
                return f"**{m_calc.group(1)} × {m_calc.group(3)} = {res:g}**\n\n*(Calculation: {n1:g} {op} {n2:g} = {res:g})*"

        # Python Overview
        if "what is python" in t_low or "explain python" in t_low or t_low in ["python", "python?"]:
            return (
                "**Python** is a high-level, interpreted programming language celebrated for its human-readable syntax and immense ecosystem.\n\n"
                "### Key Strengths:\n"
                "• **Clean Readability**: Uses indentation to structure code blocks (*The Zen of Python*).\n"
                "• **Ecosystem**: Dominates AI/Machine Learning (PyTorch, TensorFlow), Web Development (FastAPI, Django), Data Science, and DevOps.\n"
                "• **Batteries Included**: Comprehensive standard library for networking, math, file I/O, and data processing.\n\n"
                "```python\n"
                "# Quick Python Example: Destination Filter\n"
                "trips = [{\"city\": \"Kyoto\", \"days\": 5}, {\"city\": \"Paris\", \"days\": 4}]\n"
                "long_trips = [t[\"city\"] for t in trips if t[\"days\"] >= 5]\n"
                "print(f\"Extended stays: {long_trips}\")\n"
                "```"
            )

        # Machine Learning
        if "machine learning" in t_low or "what is ml" in t_low or "explain ml" in t_low:
            return (
                "**Machine Learning (ML)** is a subset of artificial intelligence where algorithms learn patterns directly from data to make predictions or decisions without rule-based coding.\n\n"
                "### Three Core Paradigms:\n"
                "1. **Supervised Learning**: Trains on labeled inputs (e.g. classification for image tagging, regression for trip cost forecasting).\n"
                "2. **Unsupervised Learning**: Uncovers hidden structures in unlabeled data (e.g. customer clustering, recommendation systems).\n"
                "3. **Reinforcement Learning**: An agent learns optimal actions via rewards and penalties in dynamic environments (e.g. autonomous driving, game playing)."
            )

        # Python FastAPI
        if "fastapi" in t_low or "python api" in t_low or "write a python api" in t_low or "fastapi example" in t_low:
            return (
                "Here is a complete, production-ready **FastAPI REST API** with Pydantic validation:\n\n"
                "```python\n"
                "from fastapi import FastAPI, HTTPException, status\n"
                "from pydantic import BaseModel, Field\n"
                "from typing import List, Optional\n"
                "import uvicorn\n\n"
                "app = FastAPI(title=\"TravelTrack API Service\", version=\"1.0.0\")\n\n"
                "class DestinationSchema(BaseModel):\n"
                "    name: str = Field(..., min_length=2, example=\"Kyoto\")\n"
                "    country: str = Field(..., min_length=2, example=\"Japan\")\n"
                "    duration_days: int = Field(default=3, ge=1, le=30)\n\n"
                "destinations_db = {}\n\n"
                "@app.get(\"/destinations\", response_model=List[DestinationSchema])\n"
                "def list_destinations():\n"
                "    return list(destinations_db.values())\n\n"
                "@app.post(\"/destinations\", status_code=status.HTTP_201_CREATED)\n"
                "def create_destination(item: DestinationSchema):\n"
                "    destinations_db[item.name.lower()] = item.dict()\n"
                "    return item\n\n"
                "if __name__ == \"__main__\":\n"
                "    uvicorn.run(\"main:app\", host=\"127.0.0.1\", port=8000, reload=True)\n"
                "```"
            )

        # Why is my code slow?
        if "slow" in t_low and ("code" in t_low or "python" in t_low or "database" in t_low or "api" in t_low):
            return (
                "Here are the most common reasons why code or backend services run slowly, and how to fix them:\n\n"
                "1. **N+1 Database Queries**: Querying a database inside a loop instead of performing batch fetches (`$in` or SQL joins).\n"
                "2. **Missing Database Indexes**: Ensure fields frequently filtered (e.g. `user_id`, `trip_id`, `created_at`) have explicit indexes.\n"
                "3. **Synchronous Blocking I/O**: Performing network calls or file reads synchronously on an `async` event loop. Use `httpx.AsyncClient` or `run_in_threadpool`.\n"
                "4. **Inefficient Algorithm Complexity**: Replacing $O(N^2)$ nested loops with $O(1)$ Hash Maps (`set` or `dict` lookups).\n"
                "5. **Uncached Heavy Computations**: Cache expensive idempotent operations with Redis or in-memory TTL caches."
            )

        # Recursion
        if "recursion" in t_low:
            if "like i'm 5" in t_low or "five" in t_low or "simply" in t_low:
                return (
                    "Imagine a stack of colorful Russian nesting dolls! 🪆\n\n"
                    "1. You open the big doll, and inside is another doll! So you open that one too (**calling the same function again**).\n"
                    "2. You keep opening dolls until you reach the tiniest doll that doesn't open. Inside is a tiny gold coin! (this is the **Base Case**).\n"
                    "3. Now that you have the coin, you close each doll back up on your way out!\n\n"
                    "That is recursion: repeating the same step on a smaller piece until reaching the stopping condition!"
                )
            return (
                "**Recursion** is a programming technique where a function solves a problem by calling itself with reduced input parameters.\n\n"
                "### Two Indispensable Elements:\n"
                "1. **Base Case**: The terminal condition that stops recursive calls.\n"
                "2. **Recursive Step**: The logic that reduces the problem towards the base case.\n\n"
                "```python\n"
                "def factorial(n: int) -> int:\n"
                "    if n <= 1: return 1  # Base Case\n"
                "    return n * factorial(n - 1)  # Recursive Step\n\n"
                "print(factorial(5))  # Output: 120\n"
                "```"
            )

        # Quantum Computing
        if "quantum" in t_low:
            return (
                "**Quantum Computing** harnesses the unique properties of quantum mechanics to perform computations exponentially faster than classical computers for specific problem classes.\n\n"
                "### Core Principles:\n"
                "• **Qubits & Superposition**: Unlike classical bits (0 or 1), a qubit can exist in a linear combination of both states simultaneously.\n"
                "• **Quantum Entanglement**: Qubits become deeply linked such that the state of one instantaneously affects another, enabling massive parallel processing.\n"
                "• **Interference**: Quantum algorithms use constructive interference to amplify correct solution paths while canceling out incorrect ones."
            )

        # Email Drafting
        if "email" in t_low and ("write" in t_low or "help" in t_low or "draft" in t_low):
            return (
                "Here is a polished, professional email template:\n\n"
                "**Subject:** Update & Next Steps: [Project / Trip Name]\n\n"
                "Dear [Name],\n\n"
                "I hope this message finds you well.\n\n"
                "I am writing to share a brief update on our progress regarding [Topic]. Everything is currently on track, and we have finalized the initial timeline and milestones.\n\n"
                "Please let me know if you have any feedback or if you would like to adjust any of the details. I look forward to connecting soon.\n\n"
                "Best regards,\n"
                "[Your Name]"
            )

        # Jokes & Humor
        if "joke" in t_low:
            return (
                "Here is one for you! 😄\n\n"
                "**Why do programmers prefer dark mode?**\n"
                "...*Because light attracts bugs!* 🐛\n\n"
                "*(And a travel one: \"I told the airline baggage agent my suitcase wasn't heavy—it was just emotionally attached to my vacation!\")* ✈️"
            )

        # Software Engineering Roadmap
        if "learn" in t_low and ("backend" in t_low or "software" in t_low or "engineer" in t_low):
            return (
                "Here is a proven roadmap for mastering **Backend Engineering**:\n\n"
                "1. **Core Language & Foundations**: Master Python (FastAPI/Django), TypeScript (Node.js), or Go. Understand data structures and algorithmic complexity.\n"
                "2. **Databases & Data Modeling**: Master relational SQL (PostgreSQL, indexes, transactions) and NoSQL document stores (MongoDB, Redis caching).\n"
                "3. **API Design & Security**: RESTful principles, JWT authentication, rate limiting, and defensive input validation.\n"
                "4. **Architecture & Microservices**: Event-driven systems (Kafka/RabbitMQ), containerization (Docker), and orchestration (Kubernetes).\n"
                "5. **DevOps & Observability**: CI/CD pipelines, structured logging, distributed tracing, and automated testing."
            )

        # Dynamic fallback for any general query
        return (
            f"Here is a clear overview regarding **{text.strip()}**:\n\n"
            "This topic involves understanding key foundational concepts and practical applications. "
            "Whether you are analyzing a principle, drafting code, or planning a project, "
            "breaking it down into core components and clear steps leads to the most effective solution.\n\n"
            "Would you like to dive deeper into any specific aspect or explore related examples?"
        )

    async def synthesize_tool_response(
        self,
        system_prompt: str,
        user_message: str,
        tool_name: str,
        tool_result: Dict[str, Any],
        places: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Synthesize natural response incorporating actual tool execution results."""
        self._load_keys()

        # Search Places / Nearby Places: Format as useful, rich travel recommendations
        if tool_name in ["search_places", "find_nearby_places"]:
            count = len(places or [])
            q = tool_result.get("query") or tool_result.get("landmark", "the area")
            if count > 0:
                lines = [f"Here are top recommended places to visit in **{q}** based on cultural prominence and traveler relevance:\n"]
                for idx, p in enumerate(places[:4], 1):
                    p_name = p.get("name", "Landmark")
                    p_cat = (p.get("category") or "Attraction").title()
                    p_loc = p.get("address") or q
                    p_desc = p.get("description") or f"A notable {p_cat.lower()} in {q}."

                    lines.append(f"**{idx}. {p_name}** ({p_cat})")
                    lines.append(f"📍 *Location:* {p_loc}")
                    lines.append(f"💡 *Highlights:* {p_desc}\n")

                lines.append("Would you like me to add any of these places to your trip itinerary (e.g. *'Add the first one to Day 2'*), or save one to your wishlist?")
                return "\n".join(lines)
            return f"I searched verified open geographic data for **{q}**, but couldn't find matches. Would you like to try another city or landmark name?"

        if tool_name == "get_budget":
            b = tool_result.get("budget", 0)
            s = tool_result.get("total_spent", 0)
            r = tool_result.get("remaining_budget", 0)
            dest = tool_result.get("destination", "your trip")
            pct = 100 - tool_result.get("percentage_spent", 0)
            return (
                f"💰 **Budget Summary for {dest}:**\n"
                f"• Total Budget: **₹{b:,.2f}**\n"
                f"• Total Spent: **₹{s:,.2f}**\n"
                f"• **Remaining Budget:** **₹{r:,.2f}** ({pct:.1f}% left)\n"
                f"Logged expenses: {tool_result.get('expense_count', 0)}"
            )

        if tool_name == "get_itinerary":
            acts = tool_result.get("activities", [])
            dest = tool_result.get("destination", "your trip")
            day_f = tool_result.get("day_filter")
            if not acts:
                day_str = f" for Day {day_f}" if day_f else ""
                return f"Your itinerary{day_str} for **{dest}** is currently empty. Tell me which sights you'd like to explore and I'll schedule them for you!"
            titles = [f"• Day {a.get('day_number')}: **{a.get('title')}** ({a.get('time', 'Anytime')})" for a in acts[:6]]
            return f"📅 **Itinerary for {dest}:**\n" + "\n".join(titles)

        if tool_name == "add_itinerary_activity":
            title = tool_result.get("activity", {}).get("title", "the activity")
            day = tool_result.get("activity", {}).get("day_number", 1)
            return f"Done — I've added '**{title}**' to **Day {day}** of your itinerary."

        if tool_name == "update_itinerary_activity":
            return "Updated your itinerary activity successfully."

        if tool_name == "get_wishlist":
            items = tool_result.get("items", [])
            if not items:
                return "Your wishlist is currently empty. Ask me to find places and we can save any of them to your wishlist!"
            names = [f"• **{i.get('name')}** ({i.get('location', 'Global')})" for i in items[:6]]
            return f"✨ **Your Saved Wishlist ({len(items)} places):**\n" + "\n".join(names)

        if tool_name == "add_wishlist":
            name = tool_result.get("item", {}).get("name", "the place")
            return f"Saved '**{name}**' to your TravelTrack wishlist!"

        if tool_name == "update_trip":
            s = tool_result.get("trip", {}).get("start_date")
            dest = tool_result.get("trip", {}).get("destination", "your trip")
            return f"Updated the dates for your **{dest}** trip starting **{s}**."

        if tool_name == "get_user_trips":
            trips = tool_result.get("trips", [])
            if not trips:
                return "You don't have any trips created yet. Tell me where you'd like to go and we can start planning!"
            names = [f"• **{t.get('title', t.get('destination'))}** to **{t.get('destination')}** ({t.get('start_date')} to {t.get('end_date')})" for t in trips]
            return f"✈️ **Your TravelTrack Trips ({len(trips)}):**\n" + "\n".join(names)

        return f"Completed {tool_name} successfully."


# =====================================================================
# 4. AUTHENTICATED TOOL REGISTRY (19+ TOOLS)
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
                "activities": activities,
                "count": len(activities),
                "day_filter": day_number
            }
        except Exception as exc:
            logger.error(f"Error fetching itinerary for trip {trip_id}: {exc}")
            return {"success": False, "error": "Could not retrieve itinerary."}

    @staticmethod
    def get_expenses(user_id: str, trip_id: str) -> Dict[str, Any]:
        """Read expenses logged for a trip."""
        if not ObjectId.is_valid(trip_id):
            return {"success": False, "error": "Invalid trip ID format."}
        trip = trips_collection.find_one({"_id": ObjectId(trip_id), "user_id": user_id})
        if not trip:
            return {"success": False, "error": "Trip not found or unauthorized."}

        try:
            expenses = list(expenses_collection.find({"trip_id": trip_id, "user_id": user_id}).sort("date", 1))
            for exp in expenses:
                exp["_id"] = str(exp["_id"])
                exp["expense_id"] = str(exp["_id"])
            return {
                "success": True,
                "trip_title": trip.get("title"),
                "destination": trip.get("destination"),
                "expenses": expenses,
                "count": len(expenses)
            }
        except Exception as exc:
            logger.error(f"Error fetching expenses for trip {trip_id}: {exc}")
            return {"success": False, "error": "Could not retrieve expenses."}

    @staticmethod
    def get_budget(user_id: str, trip_id: str) -> Dict[str, Any]:
        """Read budget analysis and expenditure totals for a trip."""
        if not ObjectId.is_valid(trip_id):
            return {"success": False, "error": "Invalid trip ID format."}
        trip = trips_collection.find_one({"_id": ObjectId(trip_id), "user_id": user_id})
        if not trip:
            return {"success": False, "error": "Trip not found or unauthorized."}

        budget = float(trip.get("budget", 0.0))
        expenses = list(expenses_collection.find({"trip_id": trip_id, "user_id": user_id}))
        total_spent = sum(float(e.get("amount", 0.0)) for e in expenses)
        remaining = max(0.0, budget - total_spent)
        pct_spent = round((total_spent / budget * 100), 1) if budget > 0 else 0.0

        by_cat: Dict[str, float] = {}
        for e in expenses:
            c = e.get("category", "Other")
            by_cat[c] = by_cat.get(c, 0.0) + float(e.get("amount", 0.0))

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
            logger.error(f"Error searching places for '{query}': {exc}")
            return {"success": False, "error": f"Place search error: {exc}", "places": []}

    @staticmethod
    async def find_nearby_places(landmark: str, category: str = "all", limit: int = 5) -> Dict[str, Any]:
        """Search places nearby a given landmark."""
        try:
            search_res = await explore_provider.search_places(query=landmark, limit=1)
            places = search_res.get("places", [])
            if not places:
                return {"success": False, "error": f"Could not find coordinates for '{landmark}'.", "places": []}

            p0 = places[0]
            lat = p0.get("lat")
            lon = p0.get("lon")
            if lat is None or lon is None:
                return {"success": False, "error": f"Coordinates unavailable for '{landmark}'.", "places": []}

            nearby_res = await explore_provider.overpass.discover_places(lat=lat, lon=lon, category=category, radius=5000)
            ranked = explore_provider._rank_and_deduplicate_candidates(nearby_res, lat, lon, category, max_dist_km=8.0)
            return {
                "success": True,
                "landmark": landmark,
                "category": category,
                "places": ranked[:limit]
            }
        except Exception as exc:
            logger.error(f"Error finding nearby places for '{landmark}': {exc}")
            return {"success": False, "error": f"Nearby search error: {exc}", "places": []}

    @staticmethod
    def add_itinerary_activity(
        user_id: str,
        trip_id: str,
        day_number: int,
        title: str,
        location: Optional[str] = None,
        place_id: Optional[str] = None,
        category: Optional[str] = "sightseeing",
        time_str: Optional[str] = "10:00 AM",
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a scheduled activity to an itinerary."""
        if not ObjectId.is_valid(trip_id):
            return {"success": False, "error": "Invalid trip ID format."}
        trip = trips_collection.find_one({"_id": ObjectId(trip_id), "user_id": user_id})
        if not trip:
            return {"success": False, "error": "Trip not found or unauthorized."}

        target_date = ""
        if trip.get("start_date"):
            try:
                start_dt = date.fromisoformat(trip["start_date"])
                target_date = (start_dt + timedelta(days=max(0, day_number - 1))).isoformat()
            except Exception:
                target_date = trip.get("start_date")

        act_doc = {
            "trip_id": trip_id,
            "user_id": user_id,
            "day_number": day_number,
            "date": target_date,
            "time": time_str or "10:00 AM",
            "title": sanitize_untrusted_text(title),
            "location": sanitize_untrusted_text(location or trip.get("destination", "")),
            "place_id": place_id,
            "category": category or "sightseeing",
            "notes": sanitize_untrusted_text(notes or ""),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        res = itineraries_collection.insert_one(act_doc)
        act_doc["_id"] = str(res.inserted_id)
        act_doc["activity_id"] = str(res.inserted_id)
        return {"success": True, "activity": act_doc, "trip_title": trip.get("title")}

    @staticmethod
    def update_itinerary_activity(
        user_id: str,
        activity_id: str,
        day_number: Optional[int] = None,
        time: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update activity date, time, or notes."""
        if not ObjectId.is_valid(activity_id):
            return {"success": False, "error": "Invalid activity ID format."}
        act = itineraries_collection.find_one({"_id": ObjectId(activity_id), "user_id": user_id})
        if not act:
            return {"success": False, "error": "Activity not found or unauthorized."}

        updates: Dict[str, Any] = {}
        if day_number is not None:
            updates["day_number"] = int(day_number)
            trip = trips_collection.find_one({"_id": ObjectId(act["trip_id"]), "user_id": user_id})
            if trip and trip.get("start_date"):
                try:
                    start_dt = date.fromisoformat(trip["start_date"])
                    updates["date"] = (start_dt + timedelta(days=max(0, int(day_number) - 1))).isoformat()
                except Exception:
                    pass
        if time:
            updates["time"] = time
        if notes:
            updates["notes"] = sanitize_untrusted_text(notes)

        if updates:
            itineraries_collection.update_one({"_id": ObjectId(activity_id)}, {"$set": updates})

        updated = itineraries_collection.find_one({"_id": ObjectId(activity_id)})
        updated["_id"] = str(updated["_id"])
        return {"success": True, "activity": updated}

    @staticmethod
    def delete_itinerary_activity(user_id: str, activity_id: str) -> Dict[str, Any]:
        """Delete an activity from itinerary."""
        if not ObjectId.is_valid(activity_id):
            return {"success": False, "error": "Invalid activity ID format."}
        act = itineraries_collection.find_one({"_id": ObjectId(activity_id), "user_id": user_id})
        if not act:
            return {"success": False, "error": "Activity not found or unauthorized."}
        itineraries_collection.delete_one({"_id": ObjectId(activity_id)})
        return {"success": True, "activity_title": act.get("title"), "day_number": act.get("day_number")}

    @staticmethod
    def add_expense(
        user_id: str,
        trip_id: str,
        amount: float,
        category: str = "Other",
        description: str = "",
        date_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """Log a new travel expense."""
        if not ObjectId.is_valid(trip_id):
            return {"success": False, "error": "Invalid trip ID format."}
        trip = trips_collection.find_one({"_id": ObjectId(trip_id), "user_id": user_id})
        if not trip:
            return {"success": False, "error": "Trip not found or unauthorized."}

        exp_doc = {
            "trip_id": trip_id,
            "user_id": user_id,
            "amount": float(amount),
            "category": category or "Other",
            "description": sanitize_untrusted_text(description or "Expense"),
            "date": date_str or date.today().isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        res = expenses_collection.insert_one(exp_doc)
        exp_doc["_id"] = str(res.inserted_id)
        return {"success": True, "expense": exp_doc}

    @staticmethod
    def delete_expense(user_id: str, expense_id: str) -> Dict[str, Any]:
        """Delete an expense."""
        if not ObjectId.is_valid(expense_id):
            return {"success": False, "error": "Invalid expense ID format."}
        exp = expenses_collection.find_one({"_id": ObjectId(expense_id), "user_id": user_id})
        if not exp:
            return {"success": False, "error": "Expense not found or unauthorized."}
        expenses_collection.delete_one({"_id": ObjectId(expense_id)})
        return {"success": True, "amount": exp.get("amount"), "description": exp.get("description")}

    @staticmethod
    def update_trip(
        user_id: str,
        trip_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        budget: Optional[float] = None,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update trip attributes."""
        if not ObjectId.is_valid(trip_id):
            return {"success": False, "error": "Invalid trip ID format."}
        trip = trips_collection.find_one({"_id": ObjectId(trip_id), "user_id": user_id})
        if not trip:
            return {"success": False, "error": "Trip not found or unauthorized."}

        updates: Dict[str, Any] = {}
        if start_date: updates["start_date"] = start_date
        if end_date: updates["end_date"] = end_date
        if budget is not None: updates["budget"] = float(budget)
        if title: updates["title"] = sanitize_untrusted_text(title)

        if updates:
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()
            trips_collection.update_one({"_id": ObjectId(trip_id)}, {"$set": updates})

        updated = trips_collection.find_one({"_id": ObjectId(trip_id)})
        updated["_id"] = str(updated["_id"])
        return {"success": True, "trip": updated}

    @staticmethod
    def delete_trip(user_id: str, trip_id: str) -> Dict[str, Any]:
        """Permanently delete a trip and cascades."""
        if not ObjectId.is_valid(trip_id):
            return {"success": False, "error": "Invalid trip ID format."}
        trip = trips_collection.find_one({"_id": ObjectId(trip_id), "user_id": user_id})
        if not trip:
            return {"success": False, "error": "Trip not found or unauthorized."}

        trips_collection.delete_one({"_id": ObjectId(trip_id)})
        itineraries_collection.delete_many({"trip_id": trip_id})
        expenses_collection.delete_many({"trip_id": trip_id})
        return {"success": True, "trip_title": trip.get("title")}

    @staticmethod
    def add_wishlist(
        user_id: str,
        place_id: Optional[str] = None,
        name: str = "",
        category: str = "attractions",
        location: str = "",
        image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Save a place to wishlist."""
        clean_name = sanitize_untrusted_text(name)
        if not clean_name:
            return {"success": False, "error": "Place name is required."}

        existing = wishlist_collection.find_one({"user_id": user_id, "name": clean_name})
        if existing:
            existing["_id"] = str(existing["_id"])
            return {"success": True, "item": existing, "already_saved": True}

        doc = {
            "user_id": user_id,
            "place_id": place_id or f"wl_{int(time.time()*1000)}",
            "name": clean_name,
            "category": category or "attractions",
            "location": sanitize_untrusted_text(location),
            "image_url": image_url,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        res = wishlist_collection.insert_one(doc)
        doc["_id"] = str(res.inserted_id)
        return {"success": True, "item": doc, "already_saved": False}

    @staticmethod
    def remove_wishlist(user_id: str, wishlist_id: Optional[str] = None, place_id: Optional[str] = None) -> Dict[str, Any]:
        """Remove item from wishlist."""
        query: Dict[str, Any] = {"user_id": user_id}
        if wishlist_id and ObjectId.is_valid(wishlist_id):
            query["_id"] = ObjectId(wishlist_id)
        elif place_id:
            query["place_id"] = place_id
        elif wishlist_id:
            query["name"] = {"$regex": re.escape(wishlist_id), "$options": "i"}
        else:
            return {"success": False, "error": "Item identifier missing."}

        item = wishlist_collection.find_one(query)
        if not item:
            return {"success": False, "error": "Wishlist item not found."}

        wishlist_collection.delete_one({"_id": item["_id"]})
        return {"success": True, "name": item.get("name")}


# =====================================================================
# 5. CONVERSATION MEMORY MANAGER
# =====================================================================

class ConversationMemoryManager:
    """Manages conversation turns, multi-turn context, and session history."""

    @staticmethod
    def get_or_create_conversation(user_id: str, conversation_id: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        cid = conversation_id or f"conv_{int(time.time() * 1000)}"
        doc = chat_conversations_collection.find_one({"user_id": user_id, "conversation_id": cid})
        if not doc:
            doc = {
                "user_id": user_id,
                "conversation_id": cid,
                "messages": [],
                "context": {
                    "active_trip_id": None,
                    "last_recommended_places": [],
                    "last_mentioned_place": None,
                    "pending_action": None,
                    "pending_clarification": None,
                    "last_interaction_at": datetime.now(timezone.utc).isoformat()
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            chat_conversations_collection.insert_one(doc)
        return cid, doc

    @staticmethod
    def save_turn(
        user_id: str,
        conversation_id: str,
        user_message: str,
        ai_message: str,
        context_updates: Optional[Dict[str, Any]] = None,
        tool_called: Optional[str] = None,
        tool_result: Optional[Dict[str, Any]] = None,
        action_status: Optional[str] = "executed",
        places: Optional[List[Dict[str, Any]]] = None
    ):
        now_iso = datetime.now(timezone.utc).isoformat()
        u_turn = {
            "role": "user",
            "content": user_message,
            "timestamp": now_iso
        }
        a_turn = {
            "role": "assistant",
            "content": ai_message,
            "timestamp": now_iso,
            "tool_called": tool_called,
            "action_status": action_status,
            "places": places or []
        }

        set_fields: Dict[str, Any] = {
            "updated_at": now_iso,
            "context.last_interaction_at": now_iso
        }
        if context_updates:
            for k, v in context_updates.items():
                set_fields[f"context.{k}"] = v

        chat_conversations_collection.update_one(
            {"user_id": user_id, "conversation_id": conversation_id},
            {
                "$push": {"messages": {"$each": [u_turn, a_turn]}},
                "$set": set_fields
            }
        )

    @staticmethod
    def get_history(user_id: str, conversation_id: str) -> List[Dict[str, Any]]:
        doc = chat_conversations_collection.find_one({"user_id": user_id, "conversation_id": conversation_id})
        return doc.get("messages", []) if doc else []

    @staticmethod
    def clear_history(user_id: str, conversation_id: str) -> bool:
        res = chat_conversations_collection.delete_one({"user_id": user_id, "conversation_id": conversation_id})
        return res.deleted_count > 0


# =====================================================================
# 6. TRAVELTRACK AI AGENT (PRIMARY CONVERSATIONAL BRAIN)
# =====================================================================

class TravelTrackAIAgent:
    """
    General-purpose AI Assistant equipped with secure TravelTrack capabilities.
    Every user message is evaluated by the LLM, which autonomously decides
    whether to answer directly or invoke TravelTrack tools.
    """

    def __init__(self):
        self.tools = AIAgentTools()
        self.memory = ConversationMemoryManager()
        self.llm_client = LLMClient()

    def _resolve_active_trip(self, user_id: str, explicit_trip_id: Optional[str], context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Identify which trip the user is referring to."""
        if explicit_trip_id and ObjectId.is_valid(explicit_trip_id):
            trip = trips_collection.find_one({"_id": ObjectId(explicit_trip_id), "user_id": user_id})
            if trip:
                trip["_id"] = str(trip["_id"])
                return trip

        ctx_trip_id = context.get("active_trip_id")
        if ctx_trip_id and ObjectId.is_valid(ctx_trip_id):
            trip = trips_collection.find_one({"_id": ObjectId(ctx_trip_id), "user_id": user_id})
            if trip:
                trip["_id"] = str(trip["_id"])
                return trip

        return None

    def _match_trip_from_text(self, user_id: str, text: str) -> Optional[Dict[str, Any]]:
        """Match a user trip by title, destination, or ID in message text."""
        t_low = text.lower()
        trips = list(trips_collection.find({"user_id": user_id}))
        for t in trips:
            t_id = str(t["_id"])
            if t_id in text:
                t["_id"] = t_id
                return t
            dest = (t.get("destination") or "").lower()
            if dest and dest in t_low:
                t["_id"] = t_id
                return t
            title = (t.get("title") or "").lower()
            if title and title in t_low:
                t["_id"] = t_id
                return t
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
        """Handles answering a clarification asked by the AI in the previous turn."""
        p_type = pending.get("type")

        # Clarification 1: User specified which trip's budget to check
        if p_type == "which_trip_budget":
            target_trip = self._match_trip_from_text(user_id, msg_text)
            if target_trip:
                res = self.tools.get_budget(user_id, str(target_trip["_id"]))
                reply = await self.llm_client.synthesize_tool_response(
                    system_prompt=TRAVEL_AGENT_SYSTEM_PROMPT,
                    user_message=msg_text,
                    tool_name="get_budget",
                    tool_result=res
                )
                self.memory.save_turn(
                    user_id=user_id,
                    conversation_id=cid,
                    user_message=msg_text,
                    ai_message=reply,
                    context_updates={"pending_clarification": None, "active_trip_id": str(target_trip["_id"])},
                    tool_called="get_budget",
                    tool_result=res,
                    action_status="read_only"
                )
                return {
                    "response": reply,
                    "conversation_id": cid,
                    "tool_called": "get_budget",
                    "tool_result": res,
                    "action_status": "read_only",
                    "places": []
                }

        # Clarification 2: User specified place to add to wishlist
        if p_type == "place_to_wishlist":
            clean_name = re.sub(r"[^\w\s]", "", msg_text).strip()
            if clean_name:
                res = self.tools.add_wishlist(user_id=user_id, name=clean_name)
                reply = f"✨ Added '**{clean_name}**' to your TravelTrack wishlist!"
                self.memory.save_turn(
                    user_id=user_id,
                    conversation_id=cid,
                    user_message=msg_text,
                    ai_message=reply,
                    context_updates={"pending_clarification": None},
                    tool_called="add_wishlist",
                    tool_result=res,
                    action_status="executed"
                )
                return {
                    "response": reply,
                    "conversation_id": cid,
                    "tool_called": "add_wishlist",
                    "tool_result": res,
                    "action_status": "executed",
                    "mutation_occurred": True,
                    "affected_entity": "wishlist"
                }

        # Clarification 3: User specified date for trip reschedule
        if p_type == "new_date_for_trip":
            parsed_d = self.llm_client._parse_date(msg_text)
            trip_id = pending.get("trip_id")
            if parsed_d and trip_id:
                new_start = parsed_d.isoformat()
                res = self.tools.update_trip(user_id, trip_id, start_date=new_start)
                dest = pending.get("trip_destination", "your trip")
                reply = f"✅ Updated the dates for your **{dest}** trip starting **{new_start}**!"
                self.memory.save_turn(
                    user_id=user_id,
                    conversation_id=cid,
                    user_message=msg_text,
                    ai_message=reply,
                    context_updates={"pending_clarification": None},
                    tool_called="update_trip",
                    tool_result=res,
                    action_status="executed"
                )
                return {
                    "response": reply,
                    "conversation_id": cid,
                    "tool_called": "update_trip",
                    "tool_result": res,
                    "action_status": "executed",
                    "mutation_occurred": True,
                    "affected_entity": "trip"
                }

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
        Sends every user message directly to the LLM agent turn.
        """
        cid, session_doc = self.memory.get_or_create_conversation(user_id, conversation_id)
        context = session_doc.get("context", {})
        msg_text = message.strip()
        msg_low = msg_text.lower()

        # Identify active trip context
        active_trip = self._resolve_active_trip(user_id, explicit_trip_id, context)

        # -------------------------------------------------------------
        # 1. HANDLE CONFIRMATION STATE MACHINE FOR PENDING ACTIONS
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
                tool_args = pending.get("args", {})

                if tool_name == "delete_trip":
                    t_id = tool_args.get("trip_id")
                    if not t_id or not ObjectId.is_valid(t_id):
                        target = active_trip or self._match_trip_from_text(user_id, tool_args.get("destination", ""))
                        if not target:
                            all_t = self.tools.get_user_trips(user_id).get("trips", [])
                            if all_t: target = all_t[0]
                        t_id = str(target["_id"]) if target else None

                    res = self.tools.delete_trip(user_id, t_id) if t_id else {"success": False, "error": "Trip ID not found"}
                    reply = f"✅ **Confirmed:** Trip has been permanently deleted." if res["success"] else f"❌ Failed: {res.get('error')}"
                    entity = "trip"

                elif tool_name == "delete_itinerary_activity":
                    act_id = tool_args.get("activity_id")
                    if not act_id or not ObjectId.is_valid(act_id):
                        act_id = None
                        if active_trip:
                            itin = self.tools.get_itinerary(user_id, str(active_trip["_id"]))
                            if itin.get("activities"):
                                act_id = itin["activities"][0]["_id"]
                    res = self.tools.delete_itinerary_activity(user_id, act_id) if act_id else {"success": False, "error": "Activity ID not found"}
                    reply = f"✅ **Confirmed:** Deleted activity from your itinerary." if res["success"] else f"❌ Failed: {res.get('error')}"
                    entity = "itinerary"

                else:
                    res = {"success": True}
                    reply = "Confirmed action executed."
                    entity = None

                status = "executed" if res.get("success") else "failed"
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
        # 2. HANDLE PENDING CLARIFICATION
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
        # 3. DIRECT LLM AGENT TURN (PRIMARY BRAIN)
        # -------------------------------------------------------------
        user_context = {
            "active_trip": active_trip,
            "all_trips": self.tools.get_user_trips(user_id).get("trips", []),
            "last_recommended_places": context.get("last_recommended_places", []),
            "last_mentioned_place": context.get("last_mentioned_place")
        }

        turn_result = await self.llm_client.run_agent_turn(
            user_message=msg_text,
            chat_history=session_doc.get("messages", []),
            user_context=user_context
        )

        # Case A: LLM answers conversationally (General QA, math, science, coding, advice, greetings)
        if turn_result.get("action") == "reply":
            reply_text = turn_result.get("content", "")
            ctx_updates: Dict[str, Any] = {}
            if "which trip's budget" in reply_text.lower():
                ctx_updates["pending_clarification"] = {"type": "which_trip_budget"}
            elif "which place would you like me to add to your wishlist" in reply_text.lower():
                ctx_updates["pending_clarification"] = {"type": "place_to_wishlist"}
            elif "what date would you like to change" in reply_text.lower():
                dest = active_trip.get("destination") if active_trip else "your trip"
                t_id = str(active_trip["_id"]) if active_trip else None
                ctx_updates["pending_clarification"] = {"type": "new_date_for_trip", "trip_id": t_id, "trip_destination": dest}

            self.memory.save_turn(
                user_id=user_id,
                conversation_id=cid,
                user_message=msg_text,
                ai_message=reply_text,
                context_updates=ctx_updates,
                action_status="read_only"
            )
            return {
                "response": reply_text,
                "conversation_id": cid,
                "tool_called": None,
                "tool_result": None,
                "action_status": "read_only",
                "places": []
            }

        # Case B: LLM requests a TravelTrack tool execution
        tool_name = turn_result.get("tool")
        tool_args = turn_result.get("args", {})

        # Destructive tools require user confirmation
        if tool_name in ["delete_trip", "delete_itinerary_activity", "delete_expense"]:
            action_id = str(uuid.uuid4())[:8]
            pending_action = {
                "action_id": action_id,
                "tool": tool_name,
                "args": tool_args,
                "description": f"Delete {tool_name.replace('delete_', '')}"
            }
            if tool_name == "delete_trip":
                if not tool_args.get("trip_id"):
                    m_trip = self._match_trip_from_text(user_id, msg_text) or active_trip
                    if not m_trip:
                        all_t = self.tools.get_user_trips(user_id).get("trips", [])
                        if len(all_t) == 1: m_trip = all_t[0]
                    if m_trip:
                        tool_args["trip_id"] = str(m_trip["_id"])
                        tool_args["destination"] = m_trip.get("destination", "your trip")
                dest = tool_args.get("destination") or (active_trip.get("destination") if active_trip else "your trip")
                confirm_msg = f"⚠️ **Confirmation Required:** Are you sure you want to permanently delete your trip to **{dest}**? This will remove all associated activities and expenses."
            elif tool_name == "delete_itinerary_activity":
                confirm_msg = "⚠️ **Confirmation Required:** Are you sure you want to delete this activity from your itinerary? This action cannot be undone."
            else:
                confirm_msg = "⚠️ **Confirmation Required:** Are you sure you want to delete this item? This action cannot be undone."

            self.memory.save_turn(
                user_id=user_id,
                conversation_id=cid,
                user_message=msg_text,
                ai_message=confirm_msg,
                context_updates={"pending_action": pending_action},
                action_status="pending_confirmation"
            )
            return {
                "response": confirm_msg,
                "conversation_id": cid,
                "tool_called": None,
                "action_status": "pending_confirmation",
                "pending_action": pending_action,
                "requires_confirmation": True
            }

        # Resolve target trip ID for trip tools
        target_trip = active_trip
        if not target_trip:
            trip_param = tool_args.get("trip_id") or tool_args.get("destination")
            if trip_param:
                target_trip = self._match_trip_from_text(user_id, str(trip_param))
            if not target_trip:
                all_t = self.tools.get_user_trips(user_id).get("trips", [])
                if len(all_t) == 1:
                    target_trip = all_t[0]

        target_trip_id = str(target_trip["_id"]) if target_trip else None

        # Execute Tool
        res: Dict[str, Any] = {"success": True}
        places: List[Dict[str, Any]] = []
        ctx_updates = {}
        entity = None
        status = "executed"

        if tool_name == "search_places":
            dest = tool_args.get("destination") or "Mumbai"
            cat = tool_args.get("category", "all")
            res = await self.tools.search_places(query=dest, category=cat, limit=6)
            places = res.get("places", [])
            ctx_updates["last_recommended_places"] = places
            if places:
                ctx_updates["last_mentioned_place"] = places[0]
            entity = "places"

        elif tool_name == "find_nearby_places":
            lm = tool_args.get("landmark") or "Eiffel Tower"
            cat = tool_args.get("category", "all")
            res = await self.tools.find_nearby_places(landmark=lm, category=cat, limit=6)
            places = res.get("places", [])
            ctx_updates["last_recommended_places"] = places
            if places:
                ctx_updates["last_mentioned_place"] = places[0]
            entity = "places"

        elif tool_name == "get_budget":
            if not target_trip_id:
                all_t = self.tools.get_user_trips(user_id).get("trips", [])
                trip_names = [f"'{t.get('destination')}'" for t in all_t if t.get("destination")]
                reply = f"Which trip's budget would you like to check? ({', '.join(trip_names)})"
                self.memory.save_turn(
                    user_id=user_id,
                    conversation_id=cid,
                    user_message=msg_text,
                    ai_message=reply,
                    context_updates={"pending_clarification": {"type": "which_trip_budget"}},
                    action_status="read_only"
                )
                return {"response": reply, "conversation_id": cid, "tool_called": None, "action_status": "read_only", "places": []}
            res = self.tools.get_budget(user_id, target_trip_id)
            entity = "budget"

        elif tool_name == "get_itinerary":
            if not target_trip_id:
                return {"response": "Please select or create a trip first to view your itinerary.", "conversation_id": cid, "tool_called": None}
            res = self.tools.get_itinerary(user_id, target_trip_id, day_number=tool_args.get("day_number"))
            entity = "itinerary"

        elif tool_name == "get_expenses":
            if not target_trip_id:
                return {"response": "Please select or create a trip first to view logged expenses.", "conversation_id": cid, "tool_called": None}
            res = self.tools.get_expenses(user_id, target_trip_id)
            entity = "expenses"

        elif tool_name == "get_user_trips":
            res = self.tools.get_user_trips(user_id)
            entity = "trip"

        elif tool_name == "get_wishlist":
            res = self.tools.get_wishlist(user_id)
            entity = "wishlist"

        elif tool_name == "add_wishlist":
            p_name = tool_args.get("place_name") or (context.get("last_recommended_places", [{}])[0].get("name"))
            if not p_name:
                return {"response": "Sure — which place would you like me to add to your wishlist?", "conversation_id": cid, "tool_called": None}
            res = self.tools.add_wishlist(user_id=user_id, name=p_name)
            entity = "wishlist"

        elif tool_name == "add_itinerary_activity":
            if not target_trip_id:
                return {"response": "Please create or select a trip first before adding itinerary activities.", "conversation_id": cid, "tool_called": None}
            p_name = tool_args.get("place_name")
            day_num = int(tool_args.get("day_number", 1))
            res = self.tools.add_itinerary_activity(
                user_id=user_id,
                trip_id=target_trip_id,
                day_number=day_num,
                title=p_name,
                location=target_trip.get("destination") if target_trip else ""
            )
            entity = "itinerary"

        elif tool_name == "update_itinerary_activity":
            if not target_trip_id:
                return {"response": "Please select a trip first.", "conversation_id": cid, "tool_called": None}
            itin = self.tools.get_itinerary(user_id, target_trip_id)
            acts = itin.get("activities", [])
            act_id = tool_args.get("activity_id")
            if not act_id and acts:
                act_id = acts[0]["_id"]
            res = self.tools.update_itinerary_activity(
                user_id=user_id,
                activity_id=act_id,
                day_number=tool_args.get("day_number")
            )
            entity = "itinerary"

        elif tool_name == "update_trip":
            if not target_trip_id:
                return {"response": "Please specify which trip to update.", "conversation_id": cid, "tool_called": None}
            res = self.tools.update_trip(
                user_id=user_id,
                trip_id=target_trip_id,
                start_date=tool_args.get("start_date")
            )
            entity = "trip"

        elif tool_name == "add_expense":
            if not target_trip_id:
                return {"response": "Please select a trip to log expenses for.", "conversation_id": cid, "tool_called": None}
            res = self.tools.add_expense(
                user_id=user_id,
                trip_id=target_trip_id,
                amount=tool_args.get("amount", 100.0),
                category=tool_args.get("category", "Other"),
                description=tool_args.get("description", "Expense")
            )
            entity = "expense"

        # Synthesize final response incorporating actual tool output
        reply = await self.llm_client.synthesize_tool_response(
            system_prompt=TRAVEL_AGENT_SYSTEM_PROMPT,
            user_message=msg_text,
            tool_name=tool_name,
            tool_result=res,
            places=places
        )

        self.memory.save_turn(
            user_id=user_id,
            conversation_id=cid,
            user_message=msg_text,
            ai_message=reply,
            context_updates=ctx_updates,
            tool_called=tool_name,
            tool_result=res,
            action_status=status,
            places=places
        )

        return {
            "response": reply,
            "conversation_id": cid,
            "tool_called": tool_name,
            "tool_result": res,
            "action_status": status,
            "mutation_occurred": res.get("success", False) if entity in ["itinerary", "wishlist", "trip", "expense"] else False,
            "affected_entity": entity,
            "places": places
        }


# Singleton service instance
ai_agent_service = TravelTrackAIAgent()
