from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_user
from app.database.mongodb import trips_collection, expenses_collection
from app.schemas.expense import ExpenseCreate, ExpenseUpdate

router = APIRouter(
    prefix="/expenses",
    tags=["Expenses"]
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
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database query error: {str(exc)}"
        )

    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found or unauthorized"
        )
    return trip


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_expense(
    expense: ExpenseCreate,
    current_user_id: str = Depends(get_current_user)
):
    """
    Log an expense for a trip owned by the current user.
    """
    verify_trip_ownership(expense.trip_id, current_user_id)

    expense_data = expense.model_dump()
    expense_data["user_id"] = current_user_id

    try:
        result = expenses_collection.insert_one(expense_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database insert error: {str(exc)}"
        )

    return {
        "message": "Expense logged successfully",
        "expense_id": str(result.inserted_id)
    }


@router.get("/trip/{trip_id}", status_code=status.HTTP_200_OK)
def get_trip_expenses(
    trip_id: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    Retrieve all expenses for a specific trip and return computed budget analytics.
    """
    trip = verify_trip_ownership(trip_id, current_user_id)
    budget = float(trip.get("budget", 0.0))

    try:
        expenses = list(
            expenses_collection.find({"trip_id": trip_id}).sort("date", -1)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database query error: {str(exc)}"
        )

    total_spent = 0.0
    by_category = {
        "Accommodation": 0.0,
        "Food": 0.0,
        "Transport": 0.0,
        "Activities": 0.0,
        "Shopping": 0.0,
        "Other": 0.0
    }

    for exp in expenses:
        exp["_id"] = str(exp["_id"])
        amt = float(exp.get("amount", 0.0))
        total_spent += amt
        cat = exp.get("category", "Other")
        if cat in by_category:
            by_category[cat] += amt
        else:
            by_category["Other"] += amt

    remaining_budget = budget - total_spent
    percentage_spent = round((total_spent / budget * 100), 1) if budget > 0 else 0.0

    return {
        "expenses": expenses,
        "summary": {
            "trip_id": trip_id,
            "budget": round(budget, 2),
            "total_spent": round(total_spent, 2),
            "remaining_budget": round(remaining_budget, 2),
            "percentage_spent": percentage_spent,
            "expense_count": len(expenses),
            "by_category": {k: round(v, 2) for k, v in by_category.items()}
        }
    }


@router.get("/user/{user_id}/summary", status_code=status.HTTP_200_OK)
def get_user_expense_summary(
    user_id: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    Retrieve overall expense metrics across all user trips for dashboard overview.
    """
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view another user's financial summary"
        )

    try:
        expenses = list(
            expenses_collection.find({"user_id": current_user_id}).sort("date", -1)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database query error: {str(exc)}"
        )

    total_spent = sum(float(exp.get("amount", 0.0)) for exp in expenses)
    by_category = {
        "Accommodation": 0.0,
        "Food": 0.0,
        "Transport": 0.0,
        "Activities": 0.0,
        "Shopping": 0.0,
        "Other": 0.0
    }
    for exp in expenses:
        cat = exp.get("category", "Other")
        amt = float(exp.get("amount", 0.0))
        if cat in by_category:
            by_category[cat] += amt
        else:
            by_category["Other"] += amt

    for exp in expenses[:5]:
        exp["_id"] = str(exp["_id"])

    return {
        "total_spent": round(total_spent, 2),
        "expense_count": len(expenses),
        "by_category": {k: round(v, 2) for k, v in by_category.items()},
        "recent_expenses": expenses[:5]
    }


@router.put("/{expense_id}", status_code=status.HTTP_200_OK)
def update_expense(
    expense_id: str,
    expense: ExpenseUpdate,
    current_user_id: str = Depends(get_current_user)
):
    """
    Update an existing expense.
    """
    if not ObjectId.is_valid(expense_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid expense ID format"
        )

    try:
        existing = expenses_collection.find_one({"_id": ObjectId(expense_id)})
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database query error: {str(exc)}"
        )

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )

    verify_trip_ownership(existing["trip_id"], current_user_id)

    update_data = {k: v for k, v in expense.model_dump().items() if v is not None}
    if not update_data:
        return {"message": "Expense updated successfully"}

    try:
        expenses_collection.update_one(
            {"_id": ObjectId(expense_id)},
            {"$set": update_data}
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database update error: {str(exc)}"
        )

    return {"message": "Expense updated successfully"}


@router.delete("/{expense_id}", status_code=status.HTTP_200_OK)
def delete_expense(
    expense_id: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    Delete an expense.
    """
    if not ObjectId.is_valid(expense_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid expense ID format"
        )

    try:
        existing = expenses_collection.find_one({"_id": ObjectId(expense_id)})
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database query error: {str(exc)}"
        )

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )

    verify_trip_ownership(existing["trip_id"], current_user_id)

    try:
        expenses_collection.delete_one({"_id": ObjectId(expense_id)})
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database delete error: {str(exc)}"
        )

    return {"message": "Expense deleted successfully"}
