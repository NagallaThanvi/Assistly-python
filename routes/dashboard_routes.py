from functools import wraps
from bson.objectid import ObjectId

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from analytics.analytics import generate_admin_charts
from models.community_model import ensure_default_communities, list_communities
from models.request_model import list_all_requests, list_open_requests_for_volunteer, list_user_requests, request_counts
from models.user_model import count_total_users, list_users


dashboard_bp = Blueprint("dashboard", __name__)


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("dashboard.user_dashboard"))
        return fn(*args, **kwargs)

    return wrapper


@dashboard_bp.route("/")
def index():
    return render_template("index.html")


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.role == "admin":
        return redirect(url_for("dashboard.admin_dashboard"))
    return redirect(url_for("dashboard.user_dashboard"))


@dashboard_bp.route("/dashboard/user")
@login_required
def user_dashboard():
    if current_user.role == "admin":
        return redirect(url_for("dashboard.admin_dashboard"))

    db = current_app.db
    ensure_default_communities(db)

    mode = current_user.doc.get("mode", "resident")
    my_requests = list_user_requests(db, current_user.id)
    volunteer_pool = list_open_requests_for_volunteer(db, current_user.id)
    communities = list_communities(db)

    return render_template(
        "dashboard.html",
        mode=mode,
        my_requests=my_requests,
        volunteer_requests=volunteer_pool,
        communities=communities,
    )


@dashboard_bp.route("/dashboard/admin")
@login_required
@admin_required
def admin_dashboard():
    db = current_app.db
    ensure_default_communities(db)

    stats = request_counts(db)
    stats["total_users"] = count_total_users(db)
    communities = list_communities(db)

    pending_user_ids: set[str] = set()
    for community in communities:
        pending = community.get("pending_requests", [])
        community["pending_count"] = len(pending)
        for user_id in pending:
            pending_user_ids.add(user_id)

    user_name_map: dict[str, str] = {}
    pending_object_ids = []
    for user_id in pending_user_ids:
        try:
            pending_object_ids.append(ObjectId(user_id))
        except Exception:
            continue

    if pending_object_ids:
        user_docs = db["users"].find({"_id": {"$in": pending_object_ids}}, {"name": 1})
        user_name_map = {str(doc["_id"]): doc.get("name", "Unknown User") for doc in user_docs}

    for community in communities:
        community["pending_users"] = [
            {
                "id": user_id,
                "name": user_name_map.get(user_id, "Unknown User"),
            }
            for user_id in community.get("pending_requests", [])
        ]

    charts = generate_admin_charts(db, "static/generated")

    return render_template(
        "admin_dashboard.html",
        stats=stats,
        users=list_users(db),
        requests=list_all_requests(db),
        communities=communities,
        charts=charts,
    )


@dashboard_bp.route("/dashboard/mode", methods=["POST"])
@login_required
def switch_mode():
    if current_user.role == "admin":
        return jsonify({"success": False, "message": "Admin mode cannot be switched."}), 400

    mode = str(request.json.get("mode", "resident")).lower() if request.is_json else request.form.get("mode", "resident")
    if mode not in {"resident", "volunteer"}:
        return jsonify({"success": False, "message": "Invalid mode."}), 400

    current_app.db["users"].update_one({"_id": current_user.doc["_id"]}, {"$set": {"mode": mode}})
    return jsonify({"success": True, "mode": mode})


@dashboard_bp.route("/dashboard/location", methods=["POST"])
@login_required
def save_location():
    payload = request.get_json(silent=True) or {}
    lat = payload.get("lat")
    lng = payload.get("lng")

    current_app.db["users"].update_one(
        {"_id": current_user.doc["_id"]},
        {"$set": {"location": {"lat": lat, "lng": lng}}},
    )
    return jsonify({"success": True, "message": "Location saved."})


@dashboard_bp.route("/notifications")
@login_required
def notifications_poll():
    db = current_app.db
    # Simple polling endpoint for bonus live updates without page refresh.
    accepted = db["requests"].count_documents({"user_id": current_user.id, "status": "In Progress"})
    completed = db["requests"].count_documents({"user_id": current_user.id, "status": "Completed"})
    return jsonify({
        "accepted_count": accepted,
        "completed_count": completed,
    })
