import os
from pathlib import Path
from pymongo import MongoClient

# Load environment variables from local .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
    backend_env = Path(__file__).resolve().parent.parent.parent / ".env"
    if backend_env.exists():
        load_dotenv(backend_env)
except ImportError:
    pass

MONGODB_URL = os.getenv("MONGODB_URL")

if not MONGODB_URL:
    raise RuntimeError(
        "MONGODB_URL environment variable is not configured. Please set it in your .env file."
    )

# Initialize MongoClient
client = MongoClient(MONGODB_URL)

# TravelTrack database and collections
DATABASE_NAME = os.getenv("DATABASE_NAME", "traveltrack")
db = client[DATABASE_NAME]
users_collection = db["users"]
trips_collection = db["trips"]