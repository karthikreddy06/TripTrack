from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routes.users import router as users_router
from app.routes.trips import router as trips_router


app = FastAPI(
    title="TravelTrack API",
    description="Production-ready REST API for TravelTrack application.",
    version="1.0.0"
)

# Configure CORS for React frontend (Vite & Create React App dev servers)
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
    """
    Root endpoint. Serves React index.html if frontend is built,
    or API welcome status otherwise.
    """
    from pathlib import Path
    root_dist = Path(__file__).resolve().parent.parent.parent / "dist" / "index.html"
    frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend-react" / "dist" / "index.html"

    target = root_dist if root_dist.exists() else frontend_dist
    if target.exists():
        from fastapi.responses import FileResponse
        return FileResponse(str(target))

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
        from app.database.mongodb import client

        # Ping MongoDB Atlas
        client.admin.command("ping")

        return {
            "status": "healthy",
            "database": "MongoDB Atlas connected"
        }
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "Database connection unavailable"
            }
        )