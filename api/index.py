import sys
from pathlib import Path
from dotenv import load_dotenv

# Add backend-fastapi directory to sys.path so app.* imports resolve properly
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend-fastapi"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# If running locally in dev, add venv site-packages so vercel dev finds installed dependencies
VENV_PACKAGES = BACKEND_DIR / "venv" / "Lib" / "site-packages"
if VENV_PACKAGES.exists() and str(VENV_PACKAGES) not in sys.path:
    sys.path.insert(0, str(VENV_PACKAGES))

# Load local .env from backend directory if present (Vercel provides env vars via process.env)
backend_env = BACKEND_DIR / ".env"
if backend_env.exists():
    load_dotenv(backend_env)
load_dotenv()

# Import the single source of truth FastAPI app from backend-fastapi
from app.main import app
