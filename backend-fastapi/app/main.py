import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routes.users import router as users_router
from app.routes.trips import router as trips_router

# Load environment variables from local .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
    backend_env = Path(__file__).resolve().parent.parent / ".env"
    if backend_env.exists():
        load_dotenv(backend_env)
except ImportError:
    pass


app = FastAPI(
    title="TravelTrack API",
    description="Production-ready REST API for TravelTrack application.",
    version="1.0.0"
)

# Configure CORS for React frontend (Vite & Create React App dev servers, Render production)
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "https://triptrack-frontend.onrender.com",
]

# Add production frontend URL from environment variable if provided
frontend_url_env = os.getenv("FRONTEND_URL")
if frontend_url_env:
    for url in frontend_url_env.split(","):
        cleaned_url = url.strip().rstrip("/")
        if cleaned_url and cleaned_url not in origins:
            origins.append(cleaned_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^https:\/\/.*\.onrender\.com$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Register API routers for root and /api prefixes
app.include_router(users_router)
app.include_router(trips_router)
app.include_router(users_router, prefix="/api")
app.include_router(trips_router, prefix="/api")


@app.get("/api", tags=["General"])
def api_home():
    """API root endpoint verifying service availability."""
    return {
        "message": "Welcome to TravelTrack API",
        "status": "running"
    }


@app.get("/", tags=["General"])
def home():
    """Root endpoint verifying API availability."""
    return {
        "message": "Welcome to TravelTrack API",
        "status": "running"
    }


@app.get("/api/health", tags=["General"])
@app.get("/health", tags=["General"])
def health_check():
    """
    Health check endpoint verifying application and database connectivity.
    Pings MongoDB Atlas without exposing credentials on failure.
    """
    try:
        from app.database.mongodb import client, DATABASE_NAME

        # Ping MongoDB Atlas
        client.admin.command("ping")

        return {
            "status": "healthy",
            "database": f"MongoDB Atlas connected ({DATABASE_NAME})"
        }
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": f"Database connection unavailable: {type(exc).__name__}"
            }
        )