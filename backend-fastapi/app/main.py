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

# Register API routers
app.include_router(users_router)
app.include_router(trips_router)


@app.get("/", tags=["General"])
def home():
    """Root endpoint verifying API availability."""
    return {
        "message": "Welcome to TravelTrack API",
        "status": "running"
    }


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