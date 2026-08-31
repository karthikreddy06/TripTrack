# TravelTrack

A full-stack travel planning and itinerary management application built with FastAPI, MongoDB Atlas, and React.

---

## Features

- **User Registration & Authentication**: Secure sign-up and login with bcrypt password hashing and signed JWT Bearer tokens.
- **Trip Planning & Management**: Create, view, update, and delete travel itineraries.
- **Search, Filtering & Sorting**: Real-time destination search, status filtering (Planned, Ongoing, Completed, Cancelled), and date/budget sorting.
- **Interactive Views**: Seamlessly switch between responsive card grid and tabular data views.
- **Responsive Dashboard**: Quick summary metrics showing Total Trips, Planned, Ongoing, Completed, and Total Budget caps.
- **Security & Multi-Tenant Data Isolation**: Strict user authorization ensuring travelers only view and edit their own itineraries.
- **Modern Botanical UI**: A calm, editorial interface designed with warm ivory tones, soft mint accents, and serif typography.

---

## Tech Stack

### Backend
- **Python 3.10+**
- **FastAPI**: High-performance asynchronous REST API framework
- **MongoDB Atlas & PyMongo**: Cloud document database
- **JWT (python-jose)**: Stateless token-based user authentication
- **bcrypt**: Cryptographic password hashing
- **Pydantic v2**: Data validation and strict request schemas

### Frontend
- **React 19**
- **Vite**: Ultra-fast frontend development and build tooling
- **React Router v7**: Client-side routing with protected route guards
- **Axios**: HTTP client with request/response interceptors
- **Lucide React**: Clean, minimal iconography
- **Vanilla CSS**: Custom design system with CSS custom properties

---

## Project Structure

```text
TravelTrack/
├── api/
│   └── index.py                 # Vercel Serverless Function entrypoint (FastAPI)
│
├── backend-fastapi/
│   ├── app/
│   │   ├── database/
│   │   │   └── mongodb.py       # MongoDB client & collection handles
│   │   ├── routes/
│   │   │   ├── users.py         # Registration & login endpoints
│   │   │   └── trips.py         # CRUD trip operations & access control
│   │   ├── schemas/
│   │   │   ├── user.py          # User registration schema
│   │   │   ├── login.py         # User login schema
│   │   │   └── trip.py          # Trip creation & update schemas
│   │   ├── auth.py              # JWT encoding, decoding & dependencies
│   │   └── main.py              # FastAPI app instance, CORS & health check
│   ├── requirements.txt         # Python backend dependencies
│   └── .env.example             # Safe template for backend variables
│
├── frontend-react/
│   ├── public/                  # Static assets & favicons
│   ├── src/
│   │   ├── components/          # Reusable UI components (Navbar, Cards, Alerts)
│   │   ├── context/             # React AuthContext provider
│   │   ├── pages/               # Views (Login, Register, Dashboard, MyTrips, Forms)
│   │   ├── services/            # Axios API client & error handling
│   │   └── styles/              # Botanical design tokens & component CSS
│   ├── package.json             # Node dependencies & scripts
│   └── .env.example             # Safe template for frontend variables
│
├── vercel.json                  # Single-project Vercel routing & build config
├── requirements.txt             # Root requirements for Vercel Python runtime
├── package.json                 # Monorepo build scripts
├── .gitignore                   # Comprehensive Git ignore rules
└── README.md                    # Project documentation
```

---

## Deploying to Vercel (One Project, One Domain)

TravelTrack is configured as a unified monorepo so that **React (frontend)** and **FastAPI (backend)** are deployed together on **one Vercel project** under a single public domain (e.g. `https://triptrack.vercel.app`).

- **Frontend**: Served at `https://triptrack.vercel.app/`
- **Backend API**: Served at `https://triptrack.vercel.app/api/...`

### 1. Import Repository into Vercel
1. Go to your [Vercel Dashboard](https://vercel.com/dashboard) and click **Add New... > Project**.
2. Select your `TripTrack` GitHub repository.
3. Keep the **Root Directory** as `./` (default).

### 2. Configure Environment Variables in Vercel
In the Vercel project setup screen, add the following under **Environment Variables**:

| Variable Name | Description | Example Value |
| :--- | :--- | :--- |
| `MONGODB_URL` | MongoDB Atlas Connection String | `mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority` |
| `DATABASE_NAME` | MongoDB database name | `traveltrack` |
| `JWT_SECRET_KEY` | Strong random secret for token signing | *(your secure secret key)* |
| `JWT_ALGORITHM` | JWT hashing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifespan in minutes | `30` |

> [!NOTE]
> `VITE_API_URL` is **not required** in production. The React frontend automatically routes requests to the same-origin `/api` path.
> The root `vercel.json` configures the static build output to `dist` and routes all API calls to `api/index.py`.

### 3. Deploy
Click **Deploy**. Vercel will run `npm run build`, output the frontend assets into `dist/`, and deploy the FastAPI backend as serverless functions under `/api/*`. Client routes (e.g. `/dashboard`, `/login`) are automatically rewritten to `/index.html` with resilient SPA fallbacks.

---

## Getting Started

### Prerequisites
- **Python 3.10+**
- **Node.js 18+** and **npm**
- **MongoDB Atlas** account (or local MongoDB server)

---

### 1. Backend Setup

1. Open a terminal and navigate to the backend directory:
   ```bash
   cd backend-fastapi
   ```

2. Create and activate a Python virtual environment:
   - **Windows (PowerShell):**
     ```powershell
     python -m venv venv
     .\venv\Scripts\activate
     ```
   - **macOS / Linux:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create your local environment configuration:
   - Copy `.env.example` to `.env`:
     - **Windows:**
       ```powershell
       copy .env.example .env
       ```
     - **macOS / Linux:**
       ```bash
       cp .env.example .env
       ```
   - Open `.env` and fill in your values:
     ```env
     MONGODB_URL=your_mongodb_atlas_connection_string
     DATABASE_NAME=traveltrack
     JWT_SECRET_KEY=replace_with_a_strong_random_secret
     JWT_ALGORITHM=HS256
     ACCESS_TOKEN_EXPIRE_MINUTES=30
     ```

5. Start the FastAPI development server:
   ```bash
   python -m uvicorn app.main:app --reload
   ```

6. The backend will be available at:
   - **API Root**: `http://127.0.0.1:8000`
   - **Interactive API Documentation (Swagger UI)**: `http://127.0.0.1:8000/docs`
   - **Alternative Docs (ReDoc)**: `http://127.0.0.1:8000/redoc`
   - **Health Check**: `http://127.0.0.1:8000/health`

---

### 2. Frontend Setup

1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend-react
   ```

2. Install Node.js packages:
   ```bash
   npm install
   ```

3. Configure your local frontend environment:
   - Copy `.env.example` to `.env`:
     - **Windows:**
       ```powershell
       copy .env.example .env
       ```
     - **macOS / Linux:**
       ```bash
       cp .env.example .env
       ```
   - Verify the API URL matches your backend:
     ```env
     VITE_API_URL=http://127.0.0.1:8000
     ```

4. Start the Vite dev server:
   ```bash
   npm run dev
   ```

5. Open your browser and navigate to:
   - **Frontend App**: `http://localhost:5173`

---

## API Reference Overview

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/users/register` | Register a new user | No |
| `POST` | `/users/login` | Log in and receive JWT token | No |
| `GET` | `/trips/{user_id}` | Retrieve all trips for a user | Yes (Bearer) |
| `POST` | `/trips/` | Create a new trip itinerary | Yes (Bearer) |
| `PUT` | `/trips/{trip_id}` | Update an existing trip | Yes (Bearer) |
| `DELETE` | `/trips/{trip_id}` | Delete a trip | Yes (Bearer) |
| `GET` | `/health` | Verify API and MongoDB health | No |
| `GET` | `/` | API welcome and status | No |

---

## Building for Production

To create an optimized production build of the React frontend:

```bash
cd frontend-react
npm run build
```

The production assets will be output to `frontend-react/dist/`.

---

## Security Best Practices

- **Never commit `.env` files**: All sensitive credentials (database connection strings, JWT secret keys) are kept in `.env` files which are strictly excluded by `.gitignore`.
- **Stateless Authorization**: All protected endpoints validate signed JWT Bearer tokens.
- **Input Validation**: Backend strictly validates all payload schemas via Pydantic.
