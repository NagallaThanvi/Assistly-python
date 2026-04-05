"""Volunteer profile and rating management."""
from datetime import datetime
from bson.objectid import ObjectId


def _volunteer_profiles(db):
    return db["volunteer_profiles"]


def _volunteer_ratings(db):
    return db["volunteer_ratings"]


def get_or_create_volunteer_profile(db, user_id: str):
    """Get volunteer profile, create if doesn't exist."""
    profile = _volunteer_profiles(db).find_one({"user_id": user_id})
    
    if not profile:
        profile_doc = {
            "user_id": user_id,
            "skills": [],
            "availability_hours": [],
            "total_helped": 0,
            "total_hours": 0,
            "average_rating": 0,
            "rating_count": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        _volunteer_profiles(db).insert_one(profile_doc)
        profile = profile_doc
    
    return profile


def update_volunteer_skills(db, user_id: str, skills: list):
    """Update volunteer's skills."""
    # Clean and lowercase skills
    skills = [s.strip().lower() for s in skills if s.strip()]
    
    return _volunteer_profiles(db).update_one(
        {"user_id": user_id},
        {
            "$set": {
                "skills": skills,
                "updated_at": datetime.utcnow(),
            }
        },
        upsert=True,
    )


def add_volunteer_rating(db, volunteer_id: str, request_id: str, rating: int, review: str = "", resident_id: str = ""):
    """Add a rating for a volunteer."""
    if not 1 <= rating <= 5:
        return {"ok": False, "reason": "Rating must be between 1 and 5"}
    
    rating_doc = {
        "volunteer_id": volunteer_id,
        "resident_id": resident_id,
        "request_id": request_id,
        "rating": rating,
        "review": review.strip(),
        "created_at": datetime.utcnow(),
    }
    
    result = _volunteer_ratings(db).insert_one(rating_doc)
    
    # Update average rating
    update_volunteer_avg_rating(db, volunteer_id)
    
    return {"ok": result.inserted_id is not None}


def update_volunteer_avg_rating(db, volunteer_id: str):
    """Recalculate average rating for volunteer."""
    ratings = list(
        _volunteer_ratings(db).aggregate([
            {"$match": {"volunteer_id": volunteer_id}},
            {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}}
        ])
    )
    
    if ratings:
        avg = ratings[0]["avg"]
        count = ratings[0]["count"]
    else:
        avg = 0
        count = 0
    
    _volunteer_profiles(db).update_one(
        {"user_id": volunteer_id},
        {
            "$set": {
                "average_rating": round(avg, 2),
                "rating_count": count,
                "updated_at": datetime.utcnow(),
            }
        },
    )


def get_volunteer_ratings(db, volunteer_id: str, limit: int = 10):
    """Get recent ratings for a volunteer."""
    return list(
        _volunteer_ratings(db)
        .find({"volunteer_id": volunteer_id})
        .sort("created_at", -1)
        .limit(limit)
    )


def get_volunteer_profile_with_stats(db, user_id: str):
    """Get volunteer profile with calculated stats."""
    profile = get_or_create_volunteer_profile(db, user_id)
    ratings = get_volunteer_ratings(db, user_id, limit=100)
    
    return {
        **profile,
        "recent_ratings": ratings[:5],
        "_id": str(profile.get("_id", "")),
    }
