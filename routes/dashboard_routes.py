from functools import wraps
from datetime import datetime
from bson.objectid import ObjectId

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models.admin_request_model import (
    get_admin_access_request,
    list_pending_admin_access_requests,
    set_admin_access_request_status,
)
from analytics.analytics import generate_admin_charts
from models.community_model import ensure_default_communities, list_communities, get_user_communities, get_community
from models.request_model import list_all_requests, list_open_requests_for_volunteer, list_open_requests_for_volunteer_in_communities, list_user_requests, request_counts
from models.user_model import count_total_users, list_users
from utils.intent_model_service import get_intent_model


dashboard_bp = Blueprint("dashboard", __name__)
MAINTAINER_EMAIL = "2410030063@gmail.com"


def is_maintainer() -> bool:
    return str(getattr(current_user, "email", "") or "").strip().lower() == MAINTAINER_EMAIL


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or (current_user.role != "admin" and not is_maintainer()):
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
    if current_user.role == "admin" or is_maintainer():
        return redirect(url_for("dashboard.admin_dashboard"))
    return redirect(url_for("dashboard.user_dashboard"))


@dashboard_bp.route("/dashboard/user")
@login_required
def user_dashboard():
    if current_user.role == "admin" or is_maintainer():
        return redirect(url_for("dashboard.admin_dashboard"))

    db = current_app.db
    ensure_default_communities(db)

    mode = current_user.doc.get("mode", "resident")
    my_requests = list_user_requests(db, current_user.id)
    
    # Get user's joined communities
    user_communities = get_user_communities(db, current_user.id)
    community_ids = [str(c["_id"]) for c in user_communities]
    
    # Only show volunteer requests from communities the user is a member of
    volunteer_pool = list_open_requests_for_volunteer_in_communities(db, current_user.id, community_ids)
    communities = list_communities(db)

    return render_template(
        "dashboard.html",
        mode=mode,
        my_requests=my_requests,
        volunteer_requests=volunteer_pool,
        communities=communities,
        user_communities=user_communities,
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

    if not is_maintainer():
        communities = [c for c in communities if str(c.get("admin_id") or "") == current_user.id]

    request_counts_by_community: dict[str, int] = {}
    for row in db["requests"].aggregate([
        {"$match": {"community_id": {"$exists": True, "$ne": None}}},
        {"$group": {"_id": "$community_id", "count": {"$sum": 1}}},
    ]):
        request_counts_by_community[str(row.get("_id"))] = int(row.get("count", 0))

    admin_user_ids: set[str] = set()
    for community in communities:
        admin_id = community.get("admin_id")
        if admin_id:
            admin_user_ids.add(admin_id)

    admin_name_map: dict[str, str] = {}
    admin_object_ids = []
    for user_id in admin_user_ids:
        try:
            admin_object_ids.append(ObjectId(user_id))
        except Exception:
            continue
    if admin_object_ids:
        admin_docs = db["users"].find({"_id": {"$in": admin_object_ids}}, {"name": 1})
        admin_name_map = {str(doc["_id"]): doc.get("name", "Unknown") for doc in admin_docs}

    pending_user_ids: set[str] = set()
    for community in communities:
        pending = community.get("pending_requests", [])
        community["pending_count"] = len(pending)
        community["request_count"] = request_counts_by_community.get(str(community["_id"]), 0)
        community["admin_name"] = admin_name_map.get(community.get("admin_id"), "Unassigned")
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

    admin_access_requests = []
    can_manage_admin_requests = is_maintainer()
    if can_manage_admin_requests:
        admin_access_requests = list_pending_admin_access_requests(db)
        for req in admin_access_requests:
            requester = None
            community = None
            try:
                requester = db["users"].find_one({"_id": ObjectId(req["user_id"])}, {"name": 1, "email": 1})
            except Exception:
                requester = None
            try:
                community = db["communities"].find_one({"_id": ObjectId(req["community_id"])}, {"name": 1, "admin_id": 1})
            except Exception:
                community = None
            req["requester_name"] = requester.get("name", "Unknown") if requester else "Unknown"
            req["requester_email"] = requester.get("email", "Unknown") if requester else "Unknown"
            req["community_name"] = community.get("name", "Unknown") if community else "Unknown"
            req["community_has_admin"] = bool(community and community.get("admin_id"))

    charts = generate_admin_charts(db, "static/generated")

    visible_requests = list_all_requests(db)
    visible_users = list_users(db)
    if not is_maintainer():
        managed_ids = {str(c.get("_id")) for c in communities}
        visible_requests = [r for r in visible_requests if str(r.get("community_id") or "") in managed_ids]

        visible_user_ids = {str(c.get("admin_id") or "") for c in communities if c.get("admin_id")}
        for c in communities:
            for member_id in c.get("members", []):
                visible_user_ids.add(str(member_id))
            for pending_id in c.get("pending_requests", []):
                visible_user_ids.add(str(pending_id))

        visible_users = [u for u in visible_users if str(u.get("_id")) in visible_user_ids]

        stats["total"] = len(visible_requests)
        stats["open"] = sum(1 for r in visible_requests if r.get("status") == "Open")
        stats["in_progress"] = sum(1 for r in visible_requests if r.get("status") == "In Progress")
        stats["completed"] = sum(1 for r in visible_requests if r.get("status") == "Completed")
        stats["total_users"] = len(visible_users)

    return render_template(
        "admin_dashboard.html",
        stats=stats,
        users=visible_users,
        requests=visible_requests,
        communities=communities,
        admin_access_requests=admin_access_requests,
        can_manage_admin_requests=can_manage_admin_requests,
        charts=charts,
    )


@dashboard_bp.route("/dashboard/admin/community/<community_id>")
@login_required
@admin_required
def community_detail(community_id):
    if not is_maintainer():
        flash("Only the maintainer can access full community oversight.", "danger")
        return redirect(url_for("dashboard.admin_dashboard"))

    db = current_app.db
    community = get_community(db, community_id)
    if not community:
        flash("Community not found.", "danger")
        return redirect(url_for("dashboard.admin_dashboard"))

    admin_name = "Unassigned"
    admin_email = "N/A"
    admin_id = community.get("admin_id")
    if admin_id:
        try:
            admin_doc = db["users"].find_one({"_id": ObjectId(admin_id)}, {"name": 1, "email": 1})
            if admin_doc:
                admin_name = admin_doc.get("name", "Unknown")
                admin_email = admin_doc.get("email", "N/A")
        except Exception:
            pass

    member_name_map: dict[str, str] = {}
    member_ids = community.get("members", [])
    member_object_ids = []
    for user_id in member_ids:
        try:
            member_object_ids.append(ObjectId(user_id))
        except Exception:
            continue
    if member_object_ids:
        member_docs = db["users"].find({"_id": {"$in": member_object_ids}}, {"name": 1})
        member_name_map = {str(doc["_id"]): doc.get("name", "Unknown User") for doc in member_docs}

    members = [
        {
            "id": user_id,
            "name": member_name_map.get(user_id, "Unknown User"),
        }
        for user_id in member_ids
    ]

    requests = list(
        db["requests"].find({"community_id": str(community["_id"])}).sort("created_at", -1).limit(50)
    )

    admin_requests = list(
        db["admin_access_requests"].find({"community_id": str(community["_id"])}).sort("created_at", -1).limit(50)
    )
    admin_request_user_ids: set[str] = {str(item.get("user_id")) for item in admin_requests if item.get("user_id")}
    admin_req_name_map: dict[str, str] = {}
    admin_req_object_ids = []
    for user_id in admin_request_user_ids:
        try:
            admin_req_object_ids.append(ObjectId(user_id))
        except Exception:
            continue
    if admin_req_object_ids:
        req_users = db["users"].find({"_id": {"$in": admin_req_object_ids}}, {"name": 1})
        admin_req_name_map = {str(doc["_id"]): doc.get("name", "Unknown User") for doc in req_users}
    for item in admin_requests:
        item["requester_name"] = admin_req_name_map.get(str(item.get("user_id")), "Unknown User")

    return render_template(
        "community_detail.html",
        community=community,
        members=members,
        admin_name=admin_name,
        admin_email=admin_email,
        community_requests=requests,
        admin_requests=admin_requests,
    )


@dashboard_bp.route("/dashboard/admin/access/<request_id>/approve", methods=["POST"])
@login_required
@admin_required
def approve_admin_access(request_id):
    if not is_maintainer():
        flash("Only the code maintainer can approve community admin requests.", "danger")
        return redirect(url_for("dashboard.admin_dashboard"))

    db = current_app.db
    req = get_admin_access_request(db, request_id)
    if not req or req.get("status") != "pending":
        flash("Admin access request not found or already handled.", "warning")
        return redirect(url_for("dashboard.admin_dashboard"))

    user_id = req.get("user_id")
    community_id = req.get("community_id")

    try:
        community_oid = ObjectId(community_id)
    except Exception:
        flash("Invalid community on request.", "danger")
        return redirect(url_for("dashboard.admin_dashboard"))

    community = db["communities"].find_one({"_id": community_oid})
    if not community:
        flash("Community not found for this request.", "danger")
        return redirect(url_for("dashboard.admin_dashboard"))

    if db["communities"].count_documents({"admin_id": user_id}) > 0:
        flash("Requester is already assigned as admin for another community.", "warning")
        set_admin_access_request_status(db, request_id, "rejected", current_user.id)
        return redirect(url_for("dashboard.admin_dashboard"))

    if community.get("admin_id") and community.get("admin_id") != user_id:
        flash("This community already has an admin. Remove/replace it first.", "warning")
        return redirect(url_for("dashboard.admin_dashboard"))

    db["communities"].update_one(
        {"_id": community_oid},
        {"$set": {"admin_id": user_id}, "$addToSet": {"members": user_id}},
    )
    db["users"].update_one({"_id": ObjectId(user_id)}, {"$set": {"role": "admin"}})
    set_admin_access_request_status(db, request_id, "approved", current_user.id)
    flash("Admin access approved and assigned to community.", "success")
    return redirect(url_for("dashboard.admin_dashboard"))


@dashboard_bp.route("/dashboard/admin/access/<request_id>/reject", methods=["POST"])
@login_required
@admin_required
def reject_admin_access(request_id):
    if not is_maintainer():
        flash("Only the code maintainer can reject community admin requests.", "danger")
        return redirect(url_for("dashboard.admin_dashboard"))

    updated = set_admin_access_request_status(current_app.db, request_id, "rejected", current_user.id)
    if not updated or updated.modified_count == 0:
        flash("Admin access request not found or already handled.", "warning")
    else:
        flash("Admin access request rejected.", "info")
    return redirect(url_for("dashboard.admin_dashboard"))


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


def _parse_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_message_from_intent(intent: str) -> str:
    intent_map = {
        "greeting": "hello",
        "request_summary": "show my request summary",
        "create_request": "create request",
        "leaderboard": "open leaderboard",
        "profile": "open profile",
        "notifications": "open notifications",
        "map_help": "show map insights",
        "help": "help",
    }
    return intent_map.get(intent, "")


def _build_assistant_response(db, user_id: str, user_name: str, mode: str, message: str):
    text = (message or "").strip()
    lowered = text.lower()

    my_total = db["requests"].count_documents({"user_id": user_id})
    my_open = db["requests"].count_documents({"user_id": user_id, "status": "Open"})
    my_progress = db["requests"].count_documents({"user_id": user_id, "status": "In Progress"})
    my_completed = db["requests"].count_documents({"user_id": user_id, "status": "Completed"})
    accepted_by_me = db["requests"].count_documents({"accepted_by": user_id})
    completed_by_me = db["requests"].count_documents({"accepted_by": user_id, "status": "Completed"})

    if any(token in lowered for token in ["hello", "hi", "hey", "start"]):
        return {
            "reply": (
                f"Hi {user_name}. You are in {mode.title()} Mode. "
                "I can help with request updates, map operations, communities, leaderboard progress, and profile guidance."
            ),
            "suggestions": [
                "Show my request summary",
                "Open leaderboard",
                "How do I create a request?",
            ],
            "action": None,
        }

    if "summary" in lowered or "status" in lowered or "my request" in lowered:
        return {
            "reply": (
                f"Current request snapshot: total {my_total}, open {my_open}, in progress {my_progress}, completed {my_completed}. "
                f"Volunteer task activity: accepted {accepted_by_me}, completed {completed_by_me}."
            ),
            "suggestions": ["Show map insights", "Open notifications", "Open profile"],
            "action": None,
        }

    if "create" in lowered and "request" in lowered:
        if mode != "resident":
            return {
                "reply": "Request creation is available only in Resident Mode. Switch mode from the dashboard top panel, then open Create Request.",
                "suggestions": ["Switch to resident mode", "Open dashboard"],
                "action": {"type": "navigate", "url": url_for("dashboard.user_dashboard")},
            }
        return {
            "reply": "You can create a request from the Create Request option in the sidebar or dashboard quick action.",
            "suggestions": ["Open create request", "Show map insights"],
            "action": {"type": "navigate", "url": url_for("requests.create_request_page")},
        }

    if "leaderboard" in lowered or "milestone" in lowered or "reward" in lowered:
        return {
            "reply": "Leaderboard score combines completed tasks, in-progress work, coverage across communities, category range, response speed, and recency bonus.",
            "suggestions": ["Open leaderboard", "How can I increase my score?"],
            "action": {"type": "navigate", "url": url_for("dashboard.leaderboard_page")},
        }

    if "profile" in lowered or "account" in lowered:
        return {
            "reply": "Your profile includes identity details, location, communities, and completed history. Keep it updated for better volunteer coordination.",
            "suggestions": ["Open profile", "Open notifications"],
            "action": {"type": "navigate", "url": url_for("dashboard.profile_page")},
        }

    if "notification" in lowered or "alert" in lowered:
        return {
            "reply": "You can monitor request lifecycle updates from the notifications page with recent status events and assignments.",
            "suggestions": ["Open notifications", "Show my request summary"],
            "action": {"type": "navigate", "url": url_for("dashboard.notifications_page")},
        }

    if "map" in lowered or "location" in lowered or "nearby" in lowered:
        return {
            "reply": "Use map quick controls to focus your location, open requests, and community coverage. You can also detect current location for accurate coordination.",
            "suggestions": ["Focus my location", "Show open requests on map"],
            "action": {"type": "map", "intent": "focus"},
        }

    if "help" in lowered:
        return {
            "reply": "Try: request summary, create request guidance, leaderboard tips, map insights, notifications, or profile updates.",
            "suggestions": ["Show my request summary", "Open leaderboard", "Open profile"],
            "action": None,
        }

    return {
        "reply": (
            "I did not fully catch that. Ask for request summary, map insights, leaderboard progress, notifications, profile updates, "
            "or request creation guidance."
        ),
        "suggestions": ["Show my request summary", "Open notifications", "Show map insights"],
        "action": None,
    }


@dashboard_bp.route("/assistant/chat", methods=["POST"])
@login_required
def assistant_chat():
    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message", "")).strip()
    if not message:
        return jsonify({"success": False, "message": "Message is required."}), 400

    mode = str(current_user.doc.get("mode", "resident"))

    intent_result = {"intent": "unknown", "confidence": 0.0}
    normalized_message = ""
    try:
        intent_result = get_intent_model().predict(message)
        normalized_message = _normalize_message_from_intent(str(intent_result.get("intent", "unknown")))
    except Exception:
        intent_result = {"intent": "unknown", "confidence": 0.0}
        normalized_message = ""

    response = _build_assistant_response(
        current_app.db,
        current_user.id,
        str(current_user.name or "there"),
        mode,
        normalized_message or message,
    )

    return jsonify(
        {
            "success": True,
            **response,
            "intent": {
                "name": intent_result.get("intent", "unknown"),
                "confidence": intent_result.get("confidence", 0.0),
                "used_model": bool(normalized_message),
            },
        }
    )


@dashboard_bp.route("/dashboard/map/data")
@login_required
def dashboard_map_data():
    db = current_app.db
    mode = str(current_user.doc.get("mode", "resident"))
    user_communities = get_user_communities(db, current_user.id)
    community_ids = [str(c.get("_id")) for c in user_communities if c.get("_id")]

    request_query = {"location": {"$exists": True, "$ne": None}}
    if mode == "resident":
        request_query["user_id"] = current_user.id
    elif community_ids:
        request_query["community_id"] = {"$in": community_ids}
    else:
        request_query["community_id"] = {"$in": []}

    request_docs = list(db["requests"].find(request_query).sort("updated_at", -1).limit(300))

    markers = []
    for doc in request_docs:
        loc = doc.get("location") or {}
        lat = _parse_float(loc.get("lat"))
        lng = _parse_float(loc.get("lng"))
        if lat is None or lng is None:
            continue

        markers.append(
            {
                "id": str(doc.get("_id")),
                "lat": lat,
                "lng": lng,
                "title": str(doc.get("title") or "Request"),
                "category": str(doc.get("category") or "General"),
                "status": str(doc.get("status") or "Open"),
                "community_id": str(doc.get("community_id") or ""),
                "is_mine": str(doc.get("user_id") or "") == current_user.id,
                "is_assigned_to_me": str(doc.get("accepted_by") or "") == current_user.id,
            }
        )

    user_loc = current_user.doc.get("location", {}) if isinstance(current_user.doc.get("location"), dict) else {}
    user_marker = {
        "lat": _parse_float(user_loc.get("lat")),
        "lng": _parse_float(user_loc.get("lng")),
    }

    return jsonify(
        {
            "success": True,
            "mode": mode,
            "markers": markers,
            "user_location": user_marker,
            "communities": [
                {
                    "id": str(c.get("_id")),
                    "name": str(c.get("name") or "Community"),
                    "location": str(c.get("location") or ""),
                }
                for c in user_communities
            ],
        }
    )


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


@dashboard_bp.route("/notifications/page")
@login_required
def notifications_page():
    db = current_app.db
    feed = []

    # Resident-side events for requests created by this user.
    for item in db["requests"].find({"user_id": current_user.id}).sort("updated_at", -1).limit(20):
        status = item.get("status", "Open")
        title = item.get("title", "Request")
        feed.append({
            "action": f"{title} is now {status}",
            "timestamp": item.get("updated_at") or item.get("created_at"),
        })

    # Volunteer-side events for requests accepted by this user.
    for item in db["requests"].find({"accepted_by": current_user.id}).sort("updated_at", -1).limit(20):
        status = item.get("status", "In Progress")
        title = item.get("title", "Volunteer request")
        feed.append({
            "action": f"You are assigned to {title} ({status})",
            "timestamp": item.get("updated_at") or item.get("created_at"),
        })

    feed.sort(key=lambda x: x.get("timestamp") or 0, reverse=True)
    return render_template("notifications.html", feed=feed[:25])


@dashboard_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile_page():
    db = current_app.db

    if request.method == "POST":
        name = str(request.form.get("name", "")).strip()
        bio = str(request.form.get("bio", "")).strip()
        if not name:
            flash("Name is required.", "warning")
            return redirect(url_for("dashboard.profile_page"))

        db["users"].update_one(
            {"_id": current_user.doc["_id"]},
            {"$set": {"name": name, "bio": bio}},
        )
        flash("Profile updated.", "success")
        return redirect(url_for("dashboard.profile_page"))

    user_doc = db["users"].find_one({"_id": current_user.doc["_id"]}) or current_user.doc
    history = list(
        db["requests"]
        .find({
            "$or": [
                {"user_id": current_user.id, "status": "Completed"},
                {"accepted_by": current_user.id, "status": "Completed"},
            ]
        })
        .sort("updated_at", -1)
        .limit(20)
    )
    communities = get_user_communities(db, current_user.id)
    location = user_doc.get("location", {}) if isinstance(user_doc.get("location"), dict) else {}

    stats = {
        "communities": len(communities),
        "requests_created": db["requests"].count_documents({"user_id": current_user.id}),
        "tasks_accepted": db["requests"].count_documents({"accepted_by": current_user.id}),
        "completed": db["requests"].count_documents({"$or": [{"user_id": current_user.id}, {"accepted_by": current_user.id}], "status": "Completed"}),
    }

    return render_template(
        "profile.html",
        user=user_doc,
        history=history,
        stats=stats,
        communities=communities,
        location=location,
    )


@dashboard_bp.route("/leaderboard")
@login_required
def leaderboard_page():
    db = current_app.db
    communities = get_user_communities(db, current_user.id)
    community_ids = [str(c["_id"]) for c in communities]

    selected_community = str(request.args.get("community_id", "")).strip()
    if selected_community and selected_community not in community_ids:
        selected_community = ""

    scope_community_ids = [selected_community] if selected_community else community_ids

    milestones = [
        {"name": "Bronze Helper", "target": 5, "reward": "Priority Support Badge", "description": "Complete 5 community tasks."},
        {"name": "Silver Responder", "target": 15, "reward": "Volunteer Spotlight", "description": "Complete 15 tasks with consistent quality."},
        {"name": "Gold Guardian", "target": 30, "reward": "Leadership Access", "description": "Complete 30 tasks and mentor new volunteers."},
        {"name": "Platinum Champion", "target": 60, "reward": "Community Reward Pack", "description": "Complete 60 tasks with sustained performance."},
    ]

    if not scope_community_ids:
        return render_template(
            "leaderboard.html",
            leaderboard=[],
            milestones=[{**m, "progress": 0, "unlocked": False} for m in milestones],
            user_completed=0,
            communities=communities,
            selected_community=selected_community,
        )

    request_docs = list(
        db["requests"].find(
            {
                "community_id": {"$in": scope_community_ids},
                "accepted_by": {"$exists": True, "$ne": None},
            }
        )
    )

    by_user: dict[str, dict] = {}
    for doc in request_docs:
        volunteer_id = str(doc.get("accepted_by") or "").strip()
        if not volunteer_id:
            continue

        bucket = by_user.setdefault(
            volunteer_id,
            {
                "completed": 0,
                "in_progress": 0,
                "accepted_total": 0,
                "categories": set(),
                "response_hours": [],
                "communities": set(),
                "last_completed_at": None,
            },
        )

        bucket["accepted_total"] += 1
        bucket["categories"].add(str(doc.get("category") or "General"))
        if doc.get("community_id"):
            bucket["communities"].add(str(doc.get("community_id")))

        status = str(doc.get("status") or "")
        if status == "Completed":
            bucket["completed"] += 1
            created_at = doc.get("created_at")
            updated_at = doc.get("updated_at") or doc.get("created_at")
            if isinstance(created_at, datetime) and isinstance(updated_at, datetime):
                delta_hours = max(0.0, (updated_at - created_at).total_seconds() / 3600)
                bucket["response_hours"].append(delta_hours)
            if isinstance(updated_at, datetime):
                if not bucket["last_completed_at"] or updated_at > bucket["last_completed_at"]:
                    bucket["last_completed_at"] = updated_at
        elif status == "In Progress":
            bucket["in_progress"] += 1

    user_ids = list(by_user.keys())
    user_name_map = {}
    if user_ids:
        object_ids = []
        for uid in user_ids:
            try:
                object_ids.append(ObjectId(uid))
            except Exception:
                continue
        if object_ids:
            for user in db["users"].find({"_id": {"$in": object_ids}}, {"name": 1, "email": 1}):
                user_name_map[str(user["_id"])] = user.get("name") or user.get("email") or "Unknown"

    leaderboard = []
    now = datetime.utcnow()

    def resolve_tier(completed_count: int):
        if completed_count >= 60:
            return "Platinum"
        if completed_count >= 30:
            return "Gold"
        if completed_count >= 15:
            return "Silver"
        if completed_count >= 5:
            return "Bronze"
        return "Starter"

    for volunteer_id, data in by_user.items():
        accepted_total = data["accepted_total"] or 1
        completed = int(data["completed"])
        in_progress = int(data["in_progress"])
        category_factor = len(data["categories"])
        coverage_factor = len(data["communities"])
        completion_rate = (completed / accepted_total) * 100
        avg_response_hours = (
            sum(data["response_hours"]) / len(data["response_hours"]) if data["response_hours"] else None
        )
        speed_factor = 0
        if avg_response_hours is not None:
            speed_factor = max(0.0, 24 - avg_response_hours) / 2

        recency_bonus = 0
        if data["last_completed_at"]:
            days_since = (now - data["last_completed_at"]).days
            if days_since <= 2:
                recency_bonus = 6
            elif days_since <= 7:
                recency_bonus = 3

        score = round((completed * 12) + (in_progress * 4) + (category_factor * 3) + (coverage_factor * 2) + speed_factor + recency_bonus, 2)

        leaderboard.append(
            {
                "user_id": volunteer_id,
                "name": user_name_map.get(volunteer_id, "Unknown Volunteer"),
                "completed": completed,
                "in_progress": in_progress,
                "accepted_total": accepted_total,
                "completion_rate": round(completion_rate, 1),
                "avg_response_hours": round(avg_response_hours, 1) if avg_response_hours is not None else None,
                "category_factor": category_factor,
                "coverage_factor": coverage_factor,
                "score": score,
                "tier": resolve_tier(completed),
                "quality": "High" if completion_rate >= 80 else ("Medium" if completion_rate >= 50 else "Needs Improvement"),
            }
        )

    leaderboard.sort(key=lambda x: (x["score"], x["completed"], x["completion_rate"]), reverse=True)
    for idx, item in enumerate(leaderboard, start=1):
        item["rank"] = idx
        if idx == 1:
            item["medal"] = "Gold"
        elif idx == 2:
            item["medal"] = "Silver"
        elif idx == 3:
            item["medal"] = "Bronze"
        else:
            item["medal"] = None

    user_completed = 0
    for item in leaderboard:
        if item["user_id"] == current_user.id:
            user_completed = item["completed"]
            break

    milestone_view = []
    for m in milestones:
        progress = min(100, int((user_completed / m["target"]) * 100)) if m["target"] else 0
        milestone_view.append({**m, "progress": progress, "unlocked": user_completed >= m["target"]})

    community_options = [
        {
            "id": str(c.get("_id")),
            "name": c.get("name", "Community"),
        }
        for c in communities
    ]

    return render_template(
        "leaderboard.html",
        leaderboard=leaderboard,
        milestones=milestone_view,
        user_completed=user_completed,
        communities=community_options,
        selected_community=selected_community,
    )
