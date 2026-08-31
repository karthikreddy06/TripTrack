import sys
from pathlib import Path

# Base paths - ensure backend-fastapi is in sys.path before any local imports
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend-fastapi"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# If running locally in dev, add venv site-packages so vercel dev / python finds installed dependencies
VENV_PACKAGES = BACKEND_DIR / "venv" / "Lib" / "site-packages"
if VENV_PACKAGES.exists() and str(VENV_PACKAGES) not in sys.path:
    sys.path.insert(0, str(VENV_PACKAGES))

# Optionally load local .env in development; in production Vercel injects environment variables directly
try:
    from dotenv import load_dotenv
    backend_env = BACKEND_DIR / ".env"
    if backend_env.exists():
        load_dotenv(backend_env)
    load_dotenv()
except ImportError:
    pass

# Import the single source of truth FastAPI app from backend-fastapi
from app.main import app

# Check for built frontend static files (check root dist first, then frontend-react/dist)
dist_dir = ROOT_DIR / "dist"
if not dist_dir.exists() or not (dist_dir / "index.html").exists():
    dist_dir = ROOT_DIR / "frontend-react" / "dist"

if dist_dir.exists() and (dist_dir / "index.html").exists():
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    from fastapi import HTTPException

    index_file = dist_dir / "index.html"
    assets_dir = dist_dir / "assets"

    # Mount /assets static directory
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # Serve index.html directly
    @app.get("/index.html", include_in_schema=False)
    def serve_index_html():
        return FileResponse(str(index_file))

    # Serve favicon assets
    favicon_svg = dist_dir / "favicon.svg"
    if favicon_svg.exists():
        @app.get("/favicon.svg", include_in_schema=False)
        @app.get("/favicon.ico", include_in_schema=False)
        def serve_favicon():
            return FileResponse(str(favicon_svg))

    # Catch-all route to serve React index.html for SPA routes (if routed through FastAPI)
    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        # Do not catch API or docs routes; let them 404 naturally if endpoint doesn't exist
        if full_path.startswith("api") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
            raise HTTPException(status_code=404, detail="Not Found")

        # Check if requested path corresponds to a static file in dist
        file_path = dist_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))

        # Default fallback to index.html for client-side routing
        return FileResponse(str(index_file))
