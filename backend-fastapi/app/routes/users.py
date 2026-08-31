from fastapi import APIRouter, HTTPException, status
import bcrypt

from app.schemas.user import UserCreate
from app.schemas.login import UserLogin
from app.database.mongodb import users_collection
from app.auth import create_access_token


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
    # Check if email already exists
    existing_user = users_collection.find_one({
        "email": user.email.lower()
    })

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
        "password": hashed_password
    }

    result = users_collection.insert_one(user_data)

    return {
        "message": "User registered successfully",
        "user_id": str(result.inserted_id)
    }


@router.post("/login", status_code=status.HTTP_200_OK)
def login_user(user: UserLogin):
    """
    Authenticate user credentials and issue a JWT access token.
    """
    # Find user by email
    existing_user = users_collection.find_one({
        "email": user.email.lower()
    })

    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Verify password against stored bcrypt hash
    password_matches = bcrypt.checkpw(
        user.password.encode("utf-8"),
        existing_user["password"].encode("utf-8")
    )

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
        "name": existing_user["name"],
        "email": existing_user["email"]
    }