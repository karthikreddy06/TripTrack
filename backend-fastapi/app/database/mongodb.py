import os
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables from .env file
load_dotenv()

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