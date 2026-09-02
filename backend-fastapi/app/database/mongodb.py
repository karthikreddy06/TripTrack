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

def get_mongodb_url() -> str:
    # Check common environment variable aliases
    url = (
        os.getenv("MONGODB_URL")
        or os.getenv("MONGODB_URI")
        or os.getenv("MONGO_URI")
        or os.getenv("DATABASE_URL")
        or ""
    ).strip()

    # Strip optional surrounding single or double quotes
    if (url.startswith('"') and url.endswith('"')) or (url.startswith("'") and url.endswith("'")):
        url = url[1:-1].strip()

    return url or "mongodb://localhost:27017"


def get_database_name() -> str:
    name = (
        os.getenv("DATABASE_NAME")
        or os.getenv("DB_NAME")
        or "traveltrack"
    ).strip()

    if (name.startswith('"') and name.endswith('"')) or (name.startswith("'") and name.endswith("'")):
        name = name[1:-1].strip()

    return name or "traveltrack"


MONGODB_URL = get_mongodb_url()
DATABASE_NAME = get_database_name()

# Initialize MongoClient with connect=False and standard 30-second timeout
client = MongoClient(
    MONGODB_URL,
    connect=False,
    serverSelectionTimeoutMS=30000,
    socketTimeoutMS=30000,
)

# TravelTrack database and collections
db = client[DATABASE_NAME]
users_collection = db["users"]
trips_collection = db["trips"]
itineraries_collection = db["itineraries"]
expenses_collection = db["expenses"]
wishlist_collection = db["wishlists"]

def init_db_indexes():
    """Ensure essential indexes exist for performance and uniqueness."""
    try:
        users_collection.create_index("email", unique=True, sparse=True)
        trips_collection.create_index("user_id")
        itineraries_collection.create_index([("trip_id", 1), ("date", 1)])
        expenses_collection.create_index([("trip_id", 1), ("date", 1)])
        expenses_collection.create_index("user_id")
        wishlist_collection.create_index([("user_id", 1), ("place_id", 1)], unique=True)
        wishlist_collection.create_index("user_id")
    except Exception as e:
        # Avoid blocking startup if connection times out initially
        pass