# TravelTrack

A production-grade, full-stack travel planning and itinerary management platform built with **FastAPI**, **MongoDB Atlas**, **React 19**, **Vite**, and **AI-assisted travel intelligence**.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    React 19 + Vite Frontend                  │
│   (Dashboard • Itinerary Timeline • Expense Tracker • AI)    │
└──────────────────────────────┬───────────────────────────────┘
                               │  HTTPS / JWT Bearer
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                     FastAPI REST Service                     │
│  (Auth Dependencies • Pydantic v2 Schemas • Rate Resilience) │
└──────────────┬───────────────────────────────┬───────────────┘
               │                               │
               ▼                               ▼
┌──────────────────────────────┐ ┌──────────────────────────────┐
│        AI Engine             │ │        MongoDB Atlas         │
│ (Gemini / OpenAI / Fallback) │ │ (users, trips, itineraries,  │
│                              │ │  expenses collections)       │
└──────────────────────────────┘ └──────────────────────────────┘
```

---

## Live Deployments

- **Frontend (Render Static Site)**: [https://triptrack-frontend.onrender.com](https://triptrack-frontend.onrender.com)
- **Backend (Render Web Service)**: [https://triptrack-backend.onrender.com](https://triptrack-backend.onrender.com)
- **Interactive OpenAPI Documentation**: [https://triptrack-backend.onrender.com/docs](https://triptrack-backend.onrender.com/docs)

---

## Features

### 1. Robust Authentication & User Isolation
- Secure user registration and login using **bcrypt** password hashing.
- Stateless, cryptographically signed **JWT access tokens** with expiration.
- Strict multi-tenant data access control preventing unauthorized resource access.

### 2. Day-by-Day Itinerary Management
- Interactive chronological timeline for visits, activities, dining, and reservations.
- Detail fields for each activity: date, time slot, venue/location, description, estimated cost, and booking notes.
- Seamless creation, modification, and deletion with instant UI synchronization.

### 3. Financial Budget & Expense Tracking
- Real-time budget progress bar tracking planned budget vs. actual logged expenses.
- Automated percentage-spent calculation and remaining balance alerts.
- Category breakdowns: `Accommodation`, `Food`, `Transport`, `Activities`, `Shopping`, `Other`.
- Interactive expense logging modal and transaction ledger.

### 4. AI Trip Planner & Travel Assistant
- AI-assisted itinerary generation based on destination, duration (1-30 days), budget cap, traveler count, travel style, and interest tags.
- Generates structured day-by-day plans, curated packing checklists, and local travel tips.
- **One-Click Save**: Instantly transforms AI itineraries into real MongoDB trips with populated activities.
- Safe server-side API key configuration (`GEMINI_API_KEY` / `OPENAI_API_KEY`) with graceful fallback mode.

### 5. AI Budget Advisor
- Evaluates trip budget pacing and real MongoDB transaction records.
- Provides health status (`on_track`, `caution`, `overbudget`), category allocation analysis, and actionable money-saving recommendations.

### 6. User Profile & Security Management
- User profile management: full name, travel bio, preferred travel style tags, and home currency.
- Secure in-app password changes requiring verification of the current password.
- Aggregated travel metrics showing total trips curated and lifetime budget managed.

### 7. Modern Botanical Editorial Design
- Custom design system featuring calming ivory tones, deep forest greens, soft mint accents, and serif headings.
- Unobtrusive global toast notifications for feedback.
- Fully responsive across mobile, tablet, laptop, and desktop viewports.

---

## Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 19, Vite, React Router v7, Axios, Lucide React, Custom CSS Design System |
| **Backend** | Python 3.10+, FastAPI, Uvicorn, Pydantic v2, PyJWT (python-jose), bcrypt |
| **Database** | MongoDB Atlas (PyMongo with connection pooling and index optimization) |
| **AI Integration** | Google Gemini API / OpenAI API (server-side only with graceful template fallback) |
| **Deployment** | Render (Web Service for Backend, Static Site for Frontend) |

---

## Project Structure

```text
TravelTrack/
├── backend-fastapi/
│   ├── app/
│   │   ├── database/
│   │   │   └── mongodb.py       # MongoDB Atlas connection & collection indexes
│   │   ├── routes/
│   │   │   ├── users.py         # Registration, login, profile & password routes
│   │   │   ├── trips.py         # Trip CRUD & cascade cleanup
│   │   │   ├── itinerary.py     # Day-by-day itinerary activities CRUD
│   │   │   ├── expenses.py      # Expense management & budget calculations
│   │   │   └── ai.py            # AI Trip Planner & AI Budget Advisor
│   │   ├── schemas/
│   │   │   ├── user.py          # User registration schema
│   │   │   ├── login.py         # Login schema
│   │   │   ├── trip.py          # Trip creation & update schemas
│   │   │   ├── itinerary.py     # Activity schemas
│   │   │   ├── expense.py       # Expense & budget summary schemas
│   │   │   ├── profile.py       # User profile & password change schemas
│   │   │   └── ai.py            # AI planning & budget advice schemas
│   │   ├── auth.py              # JWT authentication & dependency injection
│   │   └── main.py              # FastAPI app instance, CORS & router registration
│   ├── test_backend.py          # Automated backend integration test suite
│   ├── requirements.txt         # Python dependencies
│   └── .env.example             # Template for backend environment variables
│
├── frontend-react/
│   ├── src/
│   │   ├── components/          # Navbar, TripCard, TripTable, Toast, DeleteModal
│   │   ├── context/             # AuthContext, ToastContext
│   │   ├── pages/               # Dashboard, MyTrips, TripDetail, AIPlanner, Profile, CreateTrip, EditTrip
│   │   ├── services/            # Axios API client with unified error extraction
│   │   └── styles/              # Design system tokens and components CSS
│   ├── package.json             # Frontend dependencies
│   └── vite.config.js           # Vite configuration
│
└── README.md                    # Project documentation
```

---

## API Reference

All protected endpoints require an `Authorization: Bearer <token>` header.

### Authentication & User Profile
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/users/register` | Register a new user | No |
| `POST` | `/users/login` | Authenticate and retrieve JWT access token | No |
| `GET` | `/users/me` | Retrieve authenticated user profile | Yes |
| `PUT` | `/users/profile` | Update user name, bio, and preferences | Yes |
| `PUT` | `/users/change-password`| Change account password (verifies current password) | Yes |

### Trips
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/trips/` | Create a new trip | Yes |
| `GET` | `/trips/{user_id}` | Retrieve all trips for a user | Yes |
| `GET` | `/trips/single/{trip_id}`| Retrieve single trip details | Yes |
| `PUT` | `/trips/{trip_id}` | Update trip information | Yes |
| `DELETE` | `/trips/{trip_id}` | Delete trip and cascade delete activities & expenses | Yes |

### Itinerary
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/itinerary/` | Add an activity to a trip | Yes |
| `GET` | `/itinerary/trip/{trip_id}` | Retrieve chronological activities for a trip | Yes |
| `PUT` | `/itinerary/{activity_id}` | Update an activity | Yes |
| `DELETE` | `/itinerary/{activity_id}` | Delete an activity | Yes |

### Expenses & Budget
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/expenses/` | Log an expense for a trip | Yes |
| `GET` | `/expenses/trip/{trip_id}` | Retrieve trip expenses and budget summary | Yes |
| `GET` | `/expenses/user/{user_id}/summary` | Retrieve global expense metrics for dashboard | Yes |
| `PUT` | `/expenses/{expense_id}` | Update an expense record | Yes |
| `DELETE` | `/expenses/{expense_id}` | Delete an expense record | Yes |

### AI Travel Assistant
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/ai/plan-trip` | Generate structured AI travel itinerary & packing list | Yes |
| `POST` | `/ai/budget-advice` | Generate AI budget health analysis & savings tips | Yes |

### System
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `GET` | `/health` | Health check endpoint verifying MongoDB Atlas status | No |
| `GET` | `/docs` | Interactive Swagger UI API documentation | No |

---

## Local Development Setup

### 1. Prerequisites
- **Python 3.10+**
- **Node.js 18+** and **npm**
- **MongoDB Atlas** account (or local MongoDB)

---

### 2. Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend-fastapi
   ```
2. Create and activate a Python virtual environment:
   ```powershell
   # Windows PowerShell
   python -m venv venv
   .\venv\Scripts\activate
   ```
   ```bash
   # macOS / Linux
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy environment variables:
   ```bash
   cp .env.example .env
   ```
5. Configure `.env` with your settings:
   ```env
   MONGODB_URL=your_mongodb_atlas_connection_string
   DATABASE_NAME=traveltrack
   JWT_SECRET_KEY=your_strong_random_secret_key
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   FRONTEND_URL=http://localhost:5173
   # Optional AI API Key:
   GEMINI_API_KEY=your_gemini_api_key
   ```
6. Run the automated backend test suite:
   ```bash
   python test_backend.py
   ```
7. Start the FastAPI development server:
   ```bash
   python -m uvicorn app.main:app --reload --port 8000
   ```

---

### 3. Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend-react
   ```
2. Install packages:
   ```bash
   npm install
   ```
3. Create local `.env`:
   ```bash
   cp .env.example .env
   ```
   Verify `VITE_API_URL=http://127.0.0.1:8000`
4. Start the Vite development server:
   ```bash
   npm run dev
   ```
5. Open your browser at `http://localhost:5173`.

---

## Render Deployment Configuration

### 1. Backend Web Service (Render)
- **Environment**: Python 3
- **Root Directory**: `backend-fastapi`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Environment Variables**:
  - `MONGODB_URL`: *(MongoDB Atlas URI)*
  - `DATABASE_NAME`: `traveltrack`
  - `JWT_SECRET_KEY`: *(Strong secret key)*
  - `JWT_ALGORITHM`: `HS256`
  - `ACCESS_TOKEN_EXPIRE_MINUTES`: `60`
  - `FRONTEND_URL`: `https://triptrack-frontend.onrender.com`
  - `GEMINI_API_KEY`: *(Optional Google Gemini API key)*

### 2. Frontend Static Site (Render)
- **Root Directory**: `frontend-react`
- **Build Command**: `npm install && npm run build`
- **Publish Directory**: `dist`
- **Environment Variables**:
  - `VITE_API_URL`: `https://triptrack-backend.onrender.com`
- **Rewrite Rule**:
  - `/*` -> `/index.html` (Action: `Rewrite`)

---

## Security Best Practices

- **Zero Secret Exposure**: Passwords, connection strings, JWT keys, and AI keys are never committed or exposed to the client.
- **Client Sanitization**: All MongoDB queries are executed with type-safe, validated Pydantic parameters.
- **Password Protection**: User passwords are encrypted using `bcrypt` and excluded from API responses.
- **Stateless Bearer JWT Tokens**: Authenticated requests are verified on every invocation.
