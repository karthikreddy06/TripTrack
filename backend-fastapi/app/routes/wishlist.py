from datetime import datetime, timezone
from typing import List
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_user
from app.database.mongodb import wishlist_collection
from app.schemas.wishlist import (
    WishlistItemCreate,
    WishlistItemResponse,
    WishlistCheckResponse
)

router = APIRouter(prefix="/wishlist", tags=["Wishlist"])


@router.post("/", response_model=WishlistItemResponse, status_code=status.HTTP_201_CREATED)
def add_to_wishlist(
    item: WishlistItemCreate,
    current_user_id: str = Depends(get_current_user)
):
    """
    Save a destination, hotel, restaurant, attraction, or activity to the user's wishlist.
    Prevents duplicate entries.
    """
    # Check if place is already saved by this user
    existing = wishlist_collection.find_one({
        "user_id": current_user_id,
        "place_id": item.place_id
    })

    if existing:
        existing["_id"] = str(existing["_id"])
        return existing

    doc = {
        "user_id": current_user_id,
        "place_id": item.place_id,
        "name": item.name.strip(),
        "category": item.category.strip().lower(),
        "location": item.location.strip(),
        "image_url": item.image_url,
        "rating": item.rating,
        "description": item.description,
        "metadata": item.metadata or {},
        "created_at": datetime.now(timezone.utc)
    }

    result = wishlist_collection.insert_one(doc)
    doc["_id"] = str(result.inserted_id)

    return doc


@router.get("/", response_model=List[WishlistItemResponse])
def get_user_wishlist(
    current_user_id: str = Depends(get_current_user)
):
    """
    Retrieve all wishlist items for the authenticated user.
    """
    cursor = wishlist_collection.find({"user_id": current_user_id}).sort("created_at", -1)
    items = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(doc)
    return items


@router.get("/check/{place_id}", response_model=WishlistCheckResponse)
def check_place_in_wishlist(
    place_id: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    Check if a specific place is saved in the user's wishlist.
    """
    item = wishlist_collection.find_one({
        "user_id": current_user_id,
        "place_id": place_id
    })

    if item:
        return WishlistCheckResponse(is_saved=True, wishlist_id=str(item["_id"]))
    return WishlistCheckResponse(is_saved=False, wishlist_id=None)


@router.delete("/{wishlist_id}")
def remove_from_wishlist(
    wishlist_id: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    Remove an item from the user's wishlist.
    Verifies user ownership.
    """
    if not ObjectId.is_valid(wishlist_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid wishlist ID format."
        )

    result = wishlist_collection.delete_one({
        "_id": ObjectId(wishlist_id),
        "user_id": current_user_id
    })

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wishlist item not found or you do not have permission to delete it."
        )

    return {"message": "Item removed from wishlist successfully"}
