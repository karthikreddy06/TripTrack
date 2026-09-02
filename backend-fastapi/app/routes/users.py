from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
import bcrypt

from app.schemas.user import UserCreate
from app.schemas.login import UserLogin
from app.schemas.profile import ProfileUpdate, PasswordChange
from app.database.mongodb import users_collection, trips_collection
from app.auth import create_access_token, get_current_user


router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate):
    """
    Register a new user with hashed password.
    Checks for duplicate emails and returns the newly created user_id.
    """
    try:
        # Check if email already exists
        existing_user = users_collection.find_one({
            "email": user.email.lower()
        })
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection error: {str(exc)}"
        )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )

    # Hash password using bcrypt
    hashed_password = bcrypt.hashpw(
        user.password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    # Store user in MongoDB
    user_data = {
        "name": user.name.strip(),
        "email": user.email.lower(),
        "password": hashed_password,
        "bio": "",
        "travel_preferences": [],
        "home_currency": "USD"
    }

    try:
        result = users_collection.insert_one(user_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database insert error: {str(exc)}"
        )

    return {
        "message": "User registered successfully",
        "user_id": str(result.inserted_id)
    }


@router.post("/login", status_code=status.HTTP_200_OK)
def login_user(user: UserLogin):
    """
    Authenticate user credentials and issue a JWT access token.
    """
    try:
        # Find user by email
        existing_user = users_collection.find_one({
            "email": user.email.lower()
        })
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection error: {str(exc)}"
        )

    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Verify password against stored bcrypt hash
    try:
        password_matches = bcrypt.checkpw(
            user.password.encode("utf-8"),
            existing_user["password"].encode("utf-8")
        )
    except Exception:
        password_matches = False

    if not password_matches:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Create JWT access token with user_id in 'sub'
    user_id_str = str(existing_user["_id"])
    access_token = create_access_token(user_id_str)

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user_id_str,
        "name": existing_user.get("name", ""),
        "email": existing_user["email"]
    }


@router.get("/me", status_code=status.HTTP_200_OK)
def get_user_profile(current_user_id: str = Depends(get_current_user)):
    """
    Retrieve authenticated user profile information and overall statistics.
    Never exposes passwords or sensitive auth data.
    """
    if not ObjectId.is_valid(current_user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )

    try:
        user = users_collection.find_one(
            {"_id": ObjectId(current_user_id)},
            {"password": 0}  # Exclude password hash
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database query error: {str(exc)}"
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user["_id"] = str(user["_id"])
    user["user_id"] = str(user["_id"])
    return user


@router.put("/profile", status_code=status.HTTP_200_OK)
def update_user_profile(
    profile: ProfileUpdate,
    current_user_id: str = Depends(get_current_user)
):
    """
    Update profile details for the authenticated user (name, bio, preferences).
    """
    if not ObjectId.is_valid(current_user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )

    update_data = {k: v for k, v in profile.model_dump().items() if v is not None}
    if not update_data:
        return {"message": "Profile updated successfully"}

    try:
        result = users_collection.update_one(
            {"_id": ObjectId(current_user_id)},
            {"$set": update_data}
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database update error: {str(exc)}"
        )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return {"message": "Profile updated successfully"}


@router.put("/change-password", status_code=status.HTTP_200_OK)
def change_password(
    pwd_data: PasswordChange,
    current_user_id: str = Depends(get_current_user)
):
    """
    Change user password securely after verifying their current password.
    """
    if not ObjectId.is_valid(current_user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )

    try:
        user = users_collection.find_one({"_id": ObjectId(current_user_id)})
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database query error: {str(exc)}"
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify current password
    try:
        matches = bcrypt.checkpw(
            pwd_data.current_password.encode("utf-8"),
            user["password"].encode("utf-8")
        )
    except Exception:
        matches = False

    if not matches:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password does not match"
        )

    # Hash new password
    hashed_new = bcrypt.hashpw(
        pwd_data.new_password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    try:
        users_collection.update_one(
            {"_id": ObjectId(current_user_id)},
            {"$set": {"password": hashed_new}}
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database update error: {str(exc)}"
        )

    return {"message": "Password changed successfully"}