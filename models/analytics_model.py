"""Analytics and insights module."""
from datetime import datetime, timedelta
from bson.objectid import ObjectId


def _requests(db):
    return db["requests"]


def _users(db):
    return db["users"]


def _communities(db):
    return db["communities"]


def get_platform_metrics(db, days: int = 30):
    """Get platform-wide metrics for the last N days."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    total_requests = _requests(db).count_documents({})
    completed_requests = _requests(db).count_documents({"status": "Completed"})
    open_requests = _requests(db).count_documents({"status": "Open"})
    in_progress_requests = _requests(db).count_documents({"status": "In Progress"})
    
    requests_this_period = _requests(db).count_documents({"created_at": {"$gte": cutoff_date}})
    completed_this_period = _requests(db).count_documents({
        "status": "Completed",
        "updated_at": {"$gte": cutoff_date}
    })
    
    total_users = _users(db).count_documents({})
    volunteers = _users(db).count_documents({"mode": "volunteer"})
    residents = _users(db).count_documents({"mode": "resident"})
    
    avg_completion_time = get_average_completion_time(db)
    
    return {
        "total_requests": total_requests,
        "completed_requests": completed_requests,
        "open_requests": open_requests,
        "in_progress_requests": in_progress_requests,
        "completion_rate": round(
            (completed_requests / total_requests * 100) if total_requests > 0 else 0, 2
        ),
        "requests_this_period": requests_this_period,
        "completed_this_period": completed_this_period,
        "total_users": total_users,
        "active_volunteers": volunteers,
        "active_residents": residents,
        "average_completion_time_hours": avg_completion_time,
        "period_days": days,
    }


def get_community_metrics(db, community_id: str):
    """Get metrics for a specific community."""
    total_requests = _requests(db).count_documents({"community_id": community_id})
    completed = _requests(db).count_documents(
        {"community_id": community_id, "status": "Completed"}
    )
    in_progress = _requests(db).count_documents(
        {"community_id": community_id, "status": "In Progress"}
    )
    open_count = _requests(db).count_documents(
        {"community_id": community_id, "status": "Open"}
    )
    
    # Get top request categories
    categories = list(
        _requests(db).aggregate([
            {"$match": {"community_id": community_id}},
            {"$group": {"_id": "$category", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 5},
        ])
    )
    
    return {
        "total_requests": total_requests,
        "completed": completed,
        "in_progress": in_progress,
        "open": open_count,
        "completion_rate": round(
            (completed / total_requests * 100) if total_requests > 0 else 0, 2
        ),
        "top_categories": [
            {"name": c["_id"], "count": c["count"]} for c in categories
        ],
    }


def get_request_metrics_by_category(db, days: int = 30):
    """Get request statistics grouped by category."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    stats = list(
        _requests(db).aggregate([
            {"$match": {"created_at": {"$gte": cutoff_date}}},
            {
                "$group": {
                    "_id": "$category",
                    "total": {"$sum": 1},
                    "completed": {
                        "$sum": {"$cond": [{"$eq": ["$status", "Completed"]}, 1, 0]}
                    },
                    "avg_rating": {"$avg": "$rating"},
                }
            },
            {"$sort": {"total": -1}},
        ])
    )
    
    return [
        {
            "category": s["_id"],
            "total_requests": s["total"],
            "completed_requests": s["completed"],
            "completion_rate": round((s["completed"] / s["total"] * 100), 2) if s["total"] > 0 else 0,
            "average_rating": round(s["avg_rating"], 2) if s["avg_rating"] else 0,
        }
        for s in stats
    ]


def get_request_status_distribution(db, days: int = 30):
    """Get request status distribution with percentages for chart rendering."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    stats = list(
        _requests(db).aggregate([
            {"$match": {"created_at": {"$gte": cutoff_date}}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ])
    )

    total = sum(item["count"] for item in stats)
    return [
        {
            "status": item["_id"] or "Unknown",
            "count": item["count"],
            "percentage": round((item["count"] / total * 100), 2) if total > 0 else 0,
        }
        for item in stats
    ]


def get_volunteer_leaderboard(db, limit: int = 20):
    """Get leaderboard of top volunteers."""
    leaderboard = list(
        _requests(db).aggregate([
            {
                "$match": {
                    "accepted_by": {"$exists": True, "$ne": None},
                    "status": "Completed",
                }
            },
            {
                "$group": {
                    "_id": "$accepted_by",
                    "completed_requests": {"$sum": 1},
                    "avg_rating": {"$avg": "$rating"},
                    "rated_count": {"$sum": {"$cond": [{"$eq": ["$rating", None]}, 0, 1]}},
                }
            },
            {"$sort": {"completed_requests": -1}},
            {"$limit": limit},
        ])
    )
    
    return [
        {
            "volunteer_id": item["_id"],
            "completed_requests": item["completed_requests"],
            "average_rating": round(item["avg_rating"], 2) if item["avg_rating"] else 0,
            "rated_requests": item["rated_count"],
        }
        for item in leaderboard
    ]


def get_average_completion_time(db):
    """Get average time from request creation to completion."""
    results = list(
        _requests(db).aggregate([
            {
                "$match": {
                    "status": "Completed",
                    "updated_at": {"$exists": True},
                }
            },
            {
                "$project": {
                    "completion_hours": {
                        "$divide": [
                            {"$subtract": ["$updated_at", "$created_at"]},
                            (1000 * 60 * 60),  # Convert to hours
                        ]
                    }
                }
            },
            {
                "$group": {
                    "_id": None,
                    "avg_hours": {"$avg": "$completion_hours"},
                }
            },
        ])
    )
    
    if results:
        return round(results[0]["avg_hours"], 1)
    return 0


def get_daily_activity(db, days: int = 30):
    """Get daily request creation activity."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    daily_stats = list(
        _requests(db).aggregate([
            {"$match": {"created_at": {"$gte": cutoff_date}}},
            {
                "$group": {
                    "_id": {
                        "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                    },
                    "requests": {"$sum": 1},
                    "completed": {"$sum": {"$cond": [{"$eq": ["$status", "Completed"]}, 1, 0]}},
                }
            },
            {"$sort": {"_id": 1}},
        ])
    )
    
    activity_map = {
        stat["_id"]: {
            "requests": stat["requests"],
            "completed": stat["completed"],
        }
        for stat in daily_stats
    }

    result = []
    start_date = cutoff_date.date()
    for offset in range(days):
        day = start_date + timedelta(days=offset)
        day_key = day.strftime("%Y-%m-%d")
        day_data = activity_map.get(day_key, {"requests": 0, "completed": 0})
        result.append(
            {
                "date": day_key,
                "requests": day_data["requests"],
                "completed": day_data["completed"],
            }
        )

    return result


def get_user_insights(db, user_id: str):
    """Get personalized insights for a user."""
    user_requests = _requests(db).count_documents({"user_id": user_id})
    user_completed = _requests(db).count_documents(
        {"user_id": user_id, "status": "Completed"}
    )
    user_avg_rating = list(
        _requests(db).aggregate([
            {"$match": {"user_id": user_id, "rating": {"$exists": True, "$ne": None}}},
            {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}},
        ])
    )
    
    volunteer_completed = _requests(db).count_documents(
        {"accepted_by": user_id, "status": "Completed"}
    )
    volunteer_rating = list(
        _requests(db).aggregate([
            {"$match": {"accepted_by": user_id, "rating": {"$exists": True, "$ne": None}}},
            {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}},
        ])
    )
    
    return {
        "resident_requests": user_requests,
        "resident_completed": user_completed,
        "resident_avg_rating": round(user_avg_rating[0]["avg"], 2) if user_avg_rating else 0,
        "volunteer_completed": volunteer_completed,
        "volunteer_avg_rating": round(volunteer_rating[0]["avg"], 2) if volunteer_rating else 0,
        "volunteer_rating_count": volunteer_rating[0]["count"] if volunteer_rating else 0,
    }
