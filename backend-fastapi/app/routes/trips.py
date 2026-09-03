import logging
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_user
from app.database.mongodb import trips_collection, itineraries_collection, expenses_collection
from app.schemas.trip import TripCreate, TripUpdate

logger = logging.getLogger("traveltrack.trips")

router = APIRouter(
    prefix="/trips",
    tags=["Trips"]
)


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_trip(
    trip: TripCreate,
    current_user_id: str = Depends(get_current_user)
):
    """
    Create a new trip.
    Binds the trip strictly to the authenticated user ID (mass assignment prevention).
    """
    if trip.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to create a trip for another user"
        )

    trip_data = trip.model_dump()
    trip_data["user_id"] = current_user_id  # Guarantee server-side user binding

    try:
        result = trips_collection.insert_one(trip_data)
    except Exception as exc:
        logger.error(f"Database insert error creating trip: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service temporarily unavailable. Please try again."
        )

    return {
        "message": "Trip created successfully",
        "trip_id": str(result.inserted_id)
    }


@router.get("/single/{trip_id}", status_code=status.HTTP_200_OK)
def get_single_trip(
    trip_id: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    Retrieve a single trip by ID for the authenticated user.
    """
    if not ObjectId.is_valid(trip_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid trip ID format"
        )

    try:
        trip = trips_collection.find_one({
            "_id": ObjectId(trip_id),
            "user_id": current_user_id
        })
    except Exception as exc:
        logger.error(f"Database query error fetching trip {trip_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service temporarily unavailable. Please try again."
        )

    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )

    trip["_id"] = str(trip["_id"])
    return trip


@router.get("/{user_id}", status_code=status.HTTP_200_OK)
def get_user_trips(
    user_id: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    Retrieve all trips for the specified user.
    Users can only retrieve their own trips.
    """
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view another user's trips"
        )

    try:
        trips = list(trips_collection.find({"user_id": current_user_id}))
    except Exception as exc:
        logger.error(f"Database query error fetching trips for user {current_user_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service temporarily unavailable. Please try again."
        )

    for trip in trips:
        trip["_id"] = str(trip["_id"])

    return trips


@router.put("/{trip_id}", status_code=status.HTTP_200_OK)
def update_trip(
    trip_id: str,
    trip: TripUpdate,
    current_user_id: str = Depends(get_current_user)
):
    """
    Update an existing trip owned by the authenticated user.
    Returns 400 for invalid ObjectId, 404 if not found or not owned by user.
    """
    if not ObjectId.is_valid(trip_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid trip ID format"
        )

    update_data = {
        key: value
        for key, value in trip.model_dump().items()
        if value is not None
    }

    if not update_data:
        # Verify ownership and existence even when no fields are modified
        try:
            existing = trips_collection.find_one({
                "_id": ObjectId(trip_id),
                "user_id": current_user_id
            })
        except Exception as exc:
            logger.error(f"Database query error checking trip {trip_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service temporarily unavailable. Please try again."
            )

        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trip not found"
            )
        return {
            "message": "Trip updated successfully"
        }

    try:
        result = trips_collection.update_one(
            {"_id": ObjectId(trip_id), "user_id": current_user_id},
            {"$set": update_data}
        )
    except Exception as exc:
        logger.error(f"Database update error on trip {trip_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to update trip at this time."
        )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )

    return {
        "message": "Trip updated successfully"
    }


@router.delete("/{trip_id}", status_code=status.HTTP_200_OK)
def delete_trip(
    trip_id: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    Delete an existing trip owned by the authenticated user and cascade delete its activities and expenses.
    Returns 400 for invalid ObjectId, 404 if not found or not owned by user.
    """
    if not ObjectId.is_valid(trip_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid trip ID format"
        )

    try:
        result = trips_collection.delete_one({
            "_id": ObjectId(trip_id),
            "user_id": current_user_id
        })
    except Exception as exc:
        logger.error(f"Database delete error on trip {trip_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to delete trip at this time."
        )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )

    # Cascade cleanup for associated itineraries and expenses
    try:
        itineraries_collection.delete_many({"trip_id": trip_id})
        expenses_collection.delete_many({"trip_id": trip_id})
    except Exception as exc:
        logger.warning(f"Error during cascade cleanup for trip {trip_id}: {exc}")

    return {
        "message": "Trip deleted successfully"
    }