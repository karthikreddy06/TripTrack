import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routes.users import router as users_router
from app.routes.trips import router as trips_router
from app.routes.itinerary import router as itinerary_router
from app.routes.expenses import router as expenses_router
from app.routes.ai import router as ai_router
from app.routes.explore import router as explore_router
from app.routes.wishlist import router as wishlist_router
from app.database.mongodb import init_db_indexes

# Initialize indexes on startup safely
init_db_indexes()

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

import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("traveltrack.main")

# Max request body size: 2MB
MAX_REQUEST_BODY_SIZE = 2 * 1024 * 1024


class SecurityHeadersAndLimitsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Enforce request body size limit via Content-Length if present
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > MAX_REQUEST_BODY_SIZE:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Request payload exceeds maximum allowed limit (2MB)"}
                    )
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid Content-Length header"}
                )

        response = await call_next(request)

        # 2. Add standard defensive security headers
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(self), camera=(), microphone=()"

        # HSTS (Strict-Transport-Security) for HTTPS environments
        if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # 3. Dynamic API responses should not be stored by shared intermediary caches
        if "Cache-Control" not in response.headers and not request.url.path.startswith("/explore/photo"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"

        return response


app.add_middleware(SecurityHeadersAndLimitsMiddleware)

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

# Apply strictly scoped CORS middleware (No wildcard subdomain regex)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"]
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global defensive exception handler: logs the full trace internally
    while returning a sanitized, unrevealing message to clients.
    """
    logger.error(f"Unhandled server error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred. Please try again later."}
    )

# Register API routers for root and /api prefixes
app.include_router(users_router)
app.include_router(trips_router)
app.include_router(itinerary_router)
app.include_router(expenses_router)
app.include_router(ai_router)
app.include_router(explore_router)
app.include_router(wishlist_router)

app.include_router(users_router, prefix="/api")
app.include_router(trips_router, prefix="/api")
app.include_router(itinerary_router, prefix="/api")
app.include_router(expenses_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(explore_router, prefix="/api")
app.include_router(wishlist_router, prefix="/api")


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