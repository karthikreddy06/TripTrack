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
├── backend-fastapi/
│   ├── app/
│   │   ├── database/
│   │   │   └── mongodb.py       # MongoDB Atlas client & collection handles
│   │   ├── routes/
│   │   │   ├── users.py         # Registration & bcrypt login endpoints
│   │   │   └── trips.py         # CRUD trip operations & user access control
│   │   ├── schemas/
│   │   │   ├── user.py          # User registration schema
│   │   │   ├── login.py         # User login schema
│   │   │   └── trip.py          # Trip creation & update schemas
│   │   ├── auth.py              # JWT encoding, decoding & auth dependencies
│   │   └── main.py              # FastAPI app instance, CORS & health checks
│   ├── requirements.txt         # Python backend dependencies
│   └── .env.example             # Safe template for backend variables
│
├── frontend-react/
│   ├── public/                  # Static assets & icons
│   ├── src/
│   │   ├── components/          # Reusable UI components (Navbar, Cards, Alerts)
│   │   ├── context/             # React AuthContext provider
│   │   ├── pages/               # Views (Login, Register, Dashboard, MyTrips, Forms)
│   │   ├── services/            # Axios API client & error handling
│   │   └── styles/              # Botanical design tokens & component CSS
│   ├── package.json             # Frontend dependencies & scripts
│   ├── vite.config.js           # Vite configuration
│   └── .env.example             # Safe template for frontend variables
│
├── .gitignore                   # Comprehensive Git ignore rules
└── README.md                    # Project documentation
```

---

## Deploying to Render

TravelTrack is deployed to Render using a decoupled full-stack architecture:
1. **Backend**: Render Web Service (FastAPI)
2. **Frontend**: Render Static Site (React / Vite SPA)

---

### Step 1: Deploy Backend (Render Web Service)

1. In the [Render Dashboard](https://dashboard.render.com), click **New + > Web Service**.
2. Connect your `TripTrack` GitHub repository.
3. Configure the service settings:
   - **Name**: `traveltrack-api` (or your preferred name)
   - **Language**: `Python 3`
   - **Region**: Select your preferred region
   - **Branch**: `main`
   - **Root Directory**: `backend-fastapi`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

4. Add **Environment Variables** in the Render Web Service settings:

| Variable Name | Description | Example Value |
| :--- | :--- | :--- |
| `MONGODB_URL` | MongoDB Atlas Connection String | `mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority` |
| `DATABASE_NAME` | MongoDB database name | `traveltrack` |
| `JWT_SECRET_KEY` | Strong random secret for token signing | *(your secure secret key)* |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime in minutes | `30` |
| `FRONTEND_URL` | Render Frontend URL for CORS | `https://traveltrack.onrender.com` |

5. Click **Create Web Service**. Note your backend URL (e.g. `https://traveltrack-api.onrender.com`).

---

### Step 2: Deploy Frontend (Render Static Site)

1. In the [Render Dashboard](https://dashboard.render.com), click **New + > Static Site**.
2. Connect your `TripTrack` GitHub repository.
3. Configure the static site settings:
   - **Name**: `traveltrack` (or your preferred name)
   - **Branch**: `main`
   - **Root Directory**: `frontend-react`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist`

4. Add **Environment Variables** for the Static Site:

| Variable Name | Description | Example Value |
| :--- | :--- | :--- |
| `VITE_API_URL` | Render Backend Web Service URL | `https://traveltrack-api.onrender.com` |

5. Configure **Client-Side SPA Routing Rewrite Rule**:
   - In your Render Static Site dashboard, navigate to **Redirects / Rewrites**.
   - Click **Add Rule**:
     - **Source**: `/*`
     - **Destination**: `/index.html`
     - **Action**: `Rewrite`

6. Click **Create Static Site**.

7. Once deployed, update your Backend `FRONTEND_URL` environment variable if needed to match the assigned Render frontend domain.

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
