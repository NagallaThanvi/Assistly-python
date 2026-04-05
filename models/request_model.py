from datetime import datetime
from bson.objectid import ObjectId


def _requests(db):
    return db["requests"]


def create_request(db, payload: dict, user_id: str, community_id: str | None = None):
    # Parse tags from comma-separated string or list
    tags = payload.get("tags", "")
    if isinstance(tags, str):
        tags = [t.strip().lower() for t in tags.split(",") if t.strip()]
    else:
        tags = [t.strip().lower() for t in tags if t.strip()]
    
    doc = {
        "title": payload["title"].strip(),
        "description": payload["description"].strip(),
        "category": payload["category"].strip(),
        "tags": tags,
        "status": "Open",
        "user_id": user_id,
        "community_id": community_id,
        "accepted_by": None,
        "completion_confirmed": False,
        "confirmed_by_user_at": None,
        "rating": None,
        "review": None,
        "location": {
            "text": payload.get("location_text", "").strip(),
            "lat": payload.get("lat"),
            "lng": payload.get("lng"),
        },
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    return _requests(db).insert_one(doc)


def list_user_requests(db, user_id: str):
    return list(_requests(db).find({"user_id": user_id}).sort("created_at", -1))


def list_open_requests_for_volunteer(db, user_id: str):
    return list(
        _requests(db)
        .find({"status": {"$in": ["Open", "In Progress"]}, "user_id": {"$ne": user_id}})
        .sort("created_at", -1)
    )


def list_open_requests_for_volunteer_in_communities(db, user_id: str, community_ids: list):
    """Get open requests from communities the user is a member of."""
    if not community_ids:
        return []
    
    return list(
        _requests(db)
        .find({
            "community_id": {"$in": community_ids},
            "status": {"$in": ["Open", "In Progress"]},
            "user_id": {"$ne": user_id}
        })
        .sort("created_at", -1)
    )


def list_all_requests(db):
    return list(_requests(db).find({}).sort("created_at", -1))


def update_request(db, request_id: str, user_id: str, payload: dict):
    return _requests(db).update_one(
        {"_id": ObjectId(request_id), "user_id": user_id},
        {
            "$set": {
                "title": payload["title"].strip(),
                "description": payload["description"].strip(),
                "category": payload["category"].strip(),
                "updated_at": datetime.utcnow(),
            }
        },
    )


def update_request_status(db, request_id: str, user_id: str, status: str):
    return _requests(db).update_one(
        {"_id": ObjectId(request_id), "user_id": user_id},
        {"$set": {"status": status, "updated_at": datetime.utcnow()}},
    )


def delete_request(db, request_id: str, user_id: str):
    return _requests(db).delete_one({"_id": ObjectId(request_id), "user_id": user_id})


def delete_request_admin(db, request_id: str):
    return _requests(db).delete_one({"_id": ObjectId(request_id)})


def accept_request(db, request_id: str, volunteer_id: str):
    request_doc = _requests(db).find_one({"_id": ObjectId(request_id)})
    if not request_doc:
        return {"ok": False, "reason": "Request not found."}
    if request_doc.get("user_id") == volunteer_id:
        return {"ok": False, "reason": "You cannot accept your own request."}
    if request_doc.get("status") != "Open":
        return {"ok": False, "reason": "Request is no longer open."}

    updated = _requests(db).update_one(
        {"_id": ObjectId(request_id), "status": "Open"},
        {
            "$set": {
                "status": "In Progress",
                "accepted_by": volunteer_id,
                "updated_at": datetime.utcnow(),
            }
        },
    )
    return {"ok": updated.modified_count == 1, "reason": "Unable to accept request."}


def complete_request(db, request_id: str, volunteer_id: str):
    return _requests(db).update_one(
        {"_id": ObjectId(request_id), "accepted_by": volunteer_id, "status": "In Progress"},
        {"$set": {"status": "Completed", "updated_at": datetime.utcnow()}},
    )


def request_counts(db):
    total = _requests(db).count_documents({})
    completed = _requests(db).count_documents({"status": "Completed"})
    in_progress = _requests(db).count_documents({"status": "In Progress"})
    open_count = _requests(db).count_documents({"status": "Open"})
    return {
        "total": total,
        "completed": completed,
        "in_progress": in_progress,
        "open": open_count,
    }


def confirm_request_completion(db, request_id: str, user_id: str):
    """Resident confirms that the volunteer task is completed."""
    return _requests(db).update_one(
        {"_id": ObjectId(request_id), "user_id": user_id, "status": "Completed"},
        {
            "$set": {
                "completion_confirmed": True,
                "confirmed_by_user_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        },
    )


def rate_request(db, request_id: str, user_id: str, rating: int, review: str = ""):
    """Resident rates the volunteer's work (1-5 stars)."""
    if not 1 <= rating <= 5:
        return {"ok": False, "reason": "Rating must be between 1 and 5"}
    
    result = _requests(db).update_one(
        {"_id": ObjectId(request_id), "user_id": user_id},
        {
            "$set": {
                "rating": rating,
                "review": review.strip(),
                "updated_at": datetime.utcnow(),
            }
        },
    )
    return {"ok": result.modified_count == 1}


def get_request_by_id(db, request_id: str):
    try:
        return _requests(db).find_one({"_id": ObjectId(request_id)})
    except Exception:
        return None


def get_volunteer_stats(db, volunteer_id: str):
    """Get volunteer performance stats (ratings, completion rate)."""
    completed = _requests(db).count_documents(
        {"accepted_by": volunteer_id, "status": "Completed"}
    )
    rated = _requests(db).count_documents(
        {"accepted_by": volunteer_id, "rating": {"$exists": True, "$ne": None}}
    )
    
    ratings = list(
        _requests(db).aggregate([
            {"$match": {"accepted_by": volunteer_id, "rating": {"$exists": True, "$ne": None}}},
            {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}, "count": {"$sum": 1}}}
        ])
    )
    
    avg_rating = ratings[0]["avg_rating"] if ratings else 0
    
    return {
        "completed_requests": completed,
        "rated_by_users": rated,
        "average_rating": round(avg_rating, 2),
        "rating_count": rated,
    }
