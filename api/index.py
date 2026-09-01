import sys
from pathlib import Path

# Base paths - ensure backend-fastapi is in sys.path before any local imports
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend-fastapi"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

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

