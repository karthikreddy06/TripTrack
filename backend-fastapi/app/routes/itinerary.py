import logging
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_user
from app.database.mongodb import trips_collection, itineraries_collection
from app.schemas.itinerary import ActivityCreate, ActivityUpdate

logger = logging.getLogger("traveltrack.itinerary")

router = APIRouter(
    prefix="/itinerary",
    tags=["Itinerary"]
)


def verify_trip_ownership(trip_id: str, user_id: str):
    """Verify that the trip exists and is owned by the current user."""
    if not ObjectId.is_valid(trip_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid trip ID format"
        )

    try:
        trip = trips_collection.find_one({"_id": ObjectId(trip_id), "user_id": user_id})
    except Exception as exc:
        logger.error(f"Database query error checking trip ownership for trip {trip_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service temporarily unavailable. Please try again."
        )

    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found or unauthorized"
        )
    return trip


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_activity(
    activity: ActivityCreate,
    current_user_id: str = Depends(get_current_user)
):
    """
    Add a day-by-day itinerary activity to an existing trip owned by the user.
    Prevents duplicate entries on the same day while persisting verified place metadata in MongoDB.
    """
    verify_trip_ownership(activity.trip_id, current_user_id)

    # Duplicate check: check if the same activity is already scheduled on this day
    existing_act = itineraries_collection.find_one({
        "trip_id": activity.trip_id,
        "day_number": activity.day_number,
        "title": activity.title.strip()
    })

    if existing_act:
        return {
            "message": f"'{activity.title}' is already scheduled for Day {activity.day_number} of this trip.",
            "activity_id": str(existing_act["_id"]),
            "trip_id": activity.trip_id,
            "title": activity.title.strip(),
            "day_number": activity.day_number,
            "date": activity.date,
            "already_exists": True
        }

    activity_data = activity.model_dump()
    activity_data["user_id"] = current_user_id

    try:
        result = itineraries_collection.insert_one(activity_data)
    except Exception as exc:
        logger.error(f"Database insert error creating activity: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to save activity at this time."
        )

    return {
        "message": "Activity created successfully",
        "activity_id": str(result.inserted_id),
        "trip_id": activity.trip_id,
        "title": activity.title.strip(),
        "day_number": activity.day_number,
        "date": activity.date,
        "already_exists": False
    }


@router.get("/trip/{trip_id}", status_code=status.HTTP_200_OK)
def get_trip_activities(
    trip_id: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    Retrieve all activities for a trip, sorted chronologically by date and time.
    """
    verify_trip_ownership(trip_id, current_user_id)

    try:
        activities = list(
            itineraries_collection.find({"trip_id": trip_id}).sort([("date", 1), ("time", 1)])
        )
    except Exception as exc:
        logger.error(f"Database query error fetching activities for trip {trip_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service temporarily unavailable. Please try again."
        )

    for act in activities:
        act["_id"] = str(act["_id"])

    return activities


@router.put("/{activity_id}", status_code=status.HTTP_200_OK)
def update_activity(
    activity_id: str,
    activity: ActivityUpdate,
    current_user_id: str = Depends(get_current_user)
):
    """
    Update an itinerary activity.
    """
    if not ObjectId.is_valid(activity_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid activity ID format"
        )

    try:
        existing = itineraries_collection.find_one({"_id": ObjectId(activity_id)})
    except Exception as exc:
        logger.error(f"Database query error checking activity {activity_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service temporarily unavailable. Please try again."
        )

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity not found"
        )

    # Verify trip ownership
    verify_trip_ownership(existing["trip_id"], current_user_id)

    update_data = {k: v for k, v in activity.model_dump().items() if v is not None}
    if not update_data:
        return {"message": "Activity updated successfully"}

    try:
        itineraries_collection.update_one(
            {"_id": ObjectId(activity_id)},
            {"$set": update_data}
        )
    except Exception as exc:
        logger.error(f"Database update error on activity {activity_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to update activity at this time."
        )

    return {"message": "Activity updated successfully"}


@router.delete("/{activity_id}", status_code=status.HTTP_200_OK)
def delete_activity(
    activity_id: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    Delete an itinerary activity.
    """
    if not ObjectId.is_valid(activity_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid activity ID format"
        )

    try:
        existing = itineraries_collection.find_one({"_id": ObjectId(activity_id)})
    except Exception as exc:
        logger.error(f"Database query error checking activity {activity_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service temporarily unavailable. Please try again."
        )

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity not found"
        )

    # Verify trip ownership
    verify_trip_ownership(existing["trip_id"], current_user_id)

    try:
        itineraries_collection.delete_one({"_id": ObjectId(activity_id)})
    except Exception as exc:
        logger.error(f"Database delete error on activity {activity_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to delete activity at this time."
        )

    return {"message": "Activity deleted successfully"}
