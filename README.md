# TravelTrack

A production-grade, full-stack travel discovery, itinerary planning, and budget management platform built with **FastAPI**, **MongoDB Atlas**, **React 19**, **Vite**, **Leaflet Maps**, and **AI-assisted travel intelligence**.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     React 19 + Vite Frontend                     │
│  (Explore Discovery • Leaflet Map • Itineraries • Wishlist • AI) │
└──────────────────────────────┬───────────────────────────────────┘
                               │  HTTPS / JWT Bearer
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                      FastAPI REST Service                        │
│   (Auth Dependencies • Pydantic v2 • Real Places Provider)       │
└──────────────┬───────────────────────────────┬───────────────────┘
               │                               │
               ▼                               ▼
┌──────────────────────────────┐ ┌─────────────────────────────────┐
│     Places & AI Engines      │ │          MongoDB Atlas          │
│ (OSM / Nominatim / Overpass  │ │ (users, trips, itineraries,     │
│  Wikimedia / Gemini / OpenAI)│ │  expenses, wishlists collections│
└──────────────────────────────┘ └─────────────────────────────────┘
```

---

## Live Deployments

- **Frontend (Render Static Site)**: [https://triptrack-frontend.onrender.com](https://triptrack-frontend.onrender.com)
- **Backend (Render Web Service)**: [https://triptrack-backend.onrender.com](https://triptrack-backend.onrender.com)
- **Interactive OpenAPI Documentation**: [https://triptrack-backend.onrender.com/docs](https://triptrack-backend.onrender.com/docs)

---

## Features

### 1. Travel Discovery & Destination Guide (Phase 1)
- **Global Search**: Search across destinations, boutique hotels, authentic restaurants, iconic attractions, and outdoor activities.
- **Category Tabs**: Filter by `All Places`, `Destinations`, `Hotels & Stays`, `Dining & Cafes`, `Attractions`, and `Activities`.
- **Destination Discovery Guides**: Deep-dive destination hubs (e.g. `/explore/goa`, `/explore/paris`, `/explore/dubai`, `/explore/hyderabad`) featuring overviews, seasonal best times, currency info, and categorized spots.
- **Real Place Details**: Detailed profiles with addresses, opening hours, cuisine types, price tiers, amenities, and external website links.

### 2. Interactive Map Experience
- Modular **Leaflet & OpenStreetMap** interactive map rendering real coordinates and custom category pins (`hotel`, `restaurant`, `attraction`, `activity`).
- Instant popup previews with place title, location, category, and direct links.

### 3. Persistent Wishlist
- Authenticated users can save favorite destinations, stays, dining spots, and sights.
- Filter saved items by category with instant unsave and **"Add to Trip"** shortcuts.
- Backed by MongoDB Atlas `wishlists` collection with compound unique indexes preventing duplicates.

### 4. Seamless "Add to Existing Trip"
- Take any discovered place from Explore, Destination Guides, Place Details, or Wishlists and schedule it directly into an existing journey's itinerary.
- Select target trip, customize day number, time slot, and estimated expense.

### 5. Day-by-Day Itinerary Management
- Interactive chronological timeline for scheduled visits, activities, dining, and reservations.
- Detail fields for each activity: date, time slot, venue/location, description, estimated cost, and booking notes.

### 6. Financial Budget & Expense Tracking
- Real-time budget progress bar tracking planned budget vs. actual logged expenses.
- Automated percentage-spent calculation and remaining balance alerts.
- Category breakdowns: `Accommodation`, `Food`, `Transport`, `Activities`, `Shopping`, `Other`.

### 7. AI Trip Planner & AI Budget Assistant
- Structured day-by-day AI itinerary generation with packing checklists and local tips.
- **One-Click Save**: Instantly transforms AI itineraries into real MongoDB trips with populated activities.
- AI Budget diagnostics analyzing spending burn rate and generating actionable cost-saving recommendations.

### 8. User Profile & Security Management
- User profile management: full name, travel bio, preferred travel style tags, and home currency.
- Secure in-app password changes requiring verification of current password.
- Cryptographically signed JWT Bearer tokens with bcrypt password hashing.

---

## Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 19, Vite, React Router v7, Leaflet, Axios, Lucide React, Custom CSS Design System |
| **Backend** | Python 3.10+, FastAPI, Uvicorn, Pydantic v2, PyJWT (python-jose), bcrypt, HTTPX |
| **Database** | MongoDB Atlas (PyMongo with connection pooling and index optimization) |
| **Data Providers** | OpenStreetMap / Nominatim (Geocoding & POIs), Wikimedia REST API, Google Gemini / OpenAI |
| **Deployment** | Render (Web Service for Backend, Static Site for Frontend) |

---

## Project Structure

```text
TravelTrack/
├── backend-fastapi/
│   ├── app/
│   │   ├── database/
│   │   │   └── mongodb.py       # MongoDB Atlas connection & collection indexes (users, trips, itineraries, expenses, wishlists)
│   │   ├── routes/
│   │   │   ├── users.py         # Registration, login, profile & password routes
│   │   │   ├── trips.py         # Trip CRUD & cascade cleanup
│   │   │   ├── itinerary.py     # Day-by-day itinerary activities CRUD
│   │   │   ├── expenses.py      # Expense management & budget calculations
│   │   │   ├── explore.py       # Travel discovery, destination search & place details
│   │   │   ├── wishlist.py      # User-isolated Wishlist endpoints
│   │   │   └── ai.py            # AI Trip Planner & AI Budget Advisor
│   │   ├── schemas/
│   │   │   ├── user.py          # User registration schema
│   │   │   ├── trip.py          # Trip creation & update schemas
│   │   │   ├── itinerary.py     # Activity schemas
│   │   │   ├── expense.py       # Expense & budget summary schemas
│   │   │   ├── explore.py       # Explore & Place schemas
│   │   │   ├── wishlist.py      # Wishlist Pydantic schemas
│   │   │   └── ai.py            # AI planning & budget advice schemas
│   │   ├── services/
│   │   │   └── places_provider.py # Geocoding, OSM Overpass, Wikimedia & verified knowledge provider
│   │   ├── auth.py              # JWT authentication & dependency injection
│   │   └── main.py              # FastAPI app instance, CORS & router registration
│   ├── test_backend.py          # 17-part automated integration test suite
│   ├── requirements.txt         # Python dependencies
│   └── .env.example             # Template for backend environment variables
│
├── frontend-react/
│   ├── src/
│   │   ├── components/          # Navbar, PlaceCard, MapView, AddToTripModal, Toast, StatusBadge
│   │   ├── context/             # AuthContext, ToastContext
│   │   ├── pages/               # Explore, DestinationDetail, PlaceDetail, Wishlist, Dashboard, MyTrips, TripDetail, AIPlanner, Profile
│   │   ├── services/            # Axios API client with unified error extraction
│   │   └── styles/              # Design system tokens, Leaflet map styling, component CSS
│   ├── package.json             # Frontend dependencies (React 19, Leaflet, Lucide)
│   └── vite.config.js           # Vite configuration
│
└── README.md                    # Project documentation
```

---

## API Reference

All protected endpoints require an `Authorization: Bearer <token>` header.

### Explore & Travel Discovery
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `GET` | `/explore/featured` | Retrieve curated trending destinations | No |
| `GET` | `/explore/search` | Search destinations, hotels, dining, attractions | No |
| `GET` | `/explore/destinations/{destination}` | Full destination overview & categorized spots | No |
| `GET` | `/explore/places/{place_id}` | Detailed place information & nearby spots | No |
| `GET` | `/explore/hotels` | Filtered hotel discovery | No |
| `GET` | `/explore/restaurants` | Filtered restaurant discovery | No |
| `GET` | `/explore/attractions` | Filtered sights & activities discovery | No |

### Wishlist
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/wishlist/` | Save a place to user's wishlist | Yes |
| `GET` | `/wishlist/` | Retrieve all wishlist items for user | Yes |
| `GET` | `/wishlist/check/{place_id}` | Check if place is in user's wishlist | Yes |
| `DELETE` | `/wishlist/{wishlist_id}` | Remove place from wishlist | Yes |

### Trips & Itineraries
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/trips/` | Create a new trip | Yes |
| `GET` | `/trips/{user_id}` | Retrieve all trips for a user | Yes |
| `GET` | `/trips/single/{trip_id}`| Retrieve single trip details | Yes |
| `PUT` | `/trips/{trip_id}` | Update trip information | Yes |
| `DELETE` | `/trips/{trip_id}` | Delete trip and cascade delete activities & expenses | Yes |
| `POST` | `/itinerary/` | Add an activity / discovered place to a trip | Yes |
| `GET` | `/itinerary/trip/{trip_id}` | Retrieve chronological activities for a trip | Yes |
| `PUT` | `/itinerary/{activity_id}` | Update an activity | Yes |
| `DELETE` | `/itinerary/{activity_id}` | Delete an activity | Yes |

### Expenses & AI
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/expenses/` | Log an expense for a trip | Yes |
| `GET` | `/expenses/trip/{trip_id}` | Retrieve trip expenses and budget summary | Yes |
| `GET` | `/expenses/user/{user_id}/summary` | Retrieve global expense metrics | Yes |
| `POST` | `/ai/plan-trip` | Generate structured AI travel itinerary & packing list | Yes |
| `POST` | `/ai/budget-advice` | Generate AI budget health analysis & savings tips | Yes |
| `GET` | `/health` | Health check endpoint verifying MongoDB Atlas status | No |

---

## Local Development Setup

### 1. Backend Setup
1. Navigate to `backend-fastapi` and activate your virtual environment:
   ```powershell
   cd backend-fastapi
   .\venv\Scripts\activate
   ```
2. Run backend integration tests:
   ```bash
   python test_backend.py
   ```
3. Start the FastAPI development server:
   ```bash
   python -m uvicorn app.main:app --reload --port 8000
   ```

### 2. Frontend Setup
1. Navigate to `frontend-react`:
   ```bash
   cd frontend-react
   npm install
   ```
2. Start the Vite development server:
   ```bash
   npm run dev
   ```
3. Open `http://localhost:5173`.
