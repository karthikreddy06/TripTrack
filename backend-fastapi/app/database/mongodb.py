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

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "traveltrack")

# Initialize MongoClient with connect=False for serverless compatibility (avoids blocking DNS/connections on module import)
client = MongoClient(MONGODB_URL, connect=False, serverSelectionTimeoutMS=5000)

# TravelTrack database and collections
db = client[DATABASE_NAME]
users_collection = db["users"]
trips_collection = db["trips"]