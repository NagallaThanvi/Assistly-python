from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from bson.objectid import ObjectId

from models.community_model import (
    approve_join_request,
    can_manage_community,
    create_community,
    delete_community,
    ensure_default_communities,
    get_community,
    list_communities,
    reject_join_request,
    request_to_join_community,
)


communities_bp = Blueprint("communities", __name__, url_prefix="/communities")


@communities_bp.route("/")
@login_required
def communities_page():
    db = current_app.db
    ensure_default_communities(db)
    search = request.args.get("q", "").strip()
    communities = list_communities(db, search or None)

    manageable_communities = []
    pending_user_ids: set[str] = set()

    for community in communities:
        members = community.get("members", [])
        pending = community.get("pending_requests", [])

        community["is_member"] = current_user.id in members
        community["is_pending"] = current_user.id in pending
        community["can_manage"] = can_manage_community(community, current_user.id, current_user.role)
        community["member_count"] = len(members)

        if community["can_manage"]:
            manageable_communities.append(community)
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

    for community in manageable_communities:
        community["pending_users"] = [
            {
                "id": user_id,
                "name": user_name_map.get(user_id, "Unknown User"),
            }
            for user_id in community.get("pending_requests", [])
        ]

    return render_template("communities.html", communities=communities, query=search)


@communities_bp.route("/<community_id>/join", methods=["POST"])
@login_required
def join(community_id):
    status = request_to_join_community(current_app.db, community_id, current_user.id)
    if status == "not_found":
        flash("Community not found.", "danger")
    elif status == "already_member":
        flash("You are already a member of this community.", "info")
    elif status == "already_requested":
        flash("Your join request is already pending approval.", "warning")
    else:
        flash("Join request sent. Waiting for community admin approval.", "success")

    return redirect(url_for("communities.communities_page"))


@communities_bp.route("/<community_id>/approve/<user_id>", methods=["POST"])
@login_required
def approve_request(community_id, user_id):
    community = get_community(current_app.db, community_id)
    if not community:
        flash("Community not found.", "danger")
        return redirect(url_for("communities.communities_page"))

    if not can_manage_community(community, current_user.id, current_user.role):
        flash("Only this community's admin can approve requests.", "danger")
        return redirect(url_for("communities.communities_page"))

    approve_join_request(current_app.db, community_id, user_id)
    flash("Join request approved.", "success")
    return redirect(url_for("communities.communities_page"))


@communities_bp.route("/<community_id>/reject/<user_id>", methods=["POST"])
@login_required
def reject_request(community_id, user_id):
    community = get_community(current_app.db, community_id)
    if not community:
        flash("Community not found.", "danger")
        return redirect(url_for("communities.communities_page"))

    if not can_manage_community(community, current_user.id, current_user.role):
        flash("Only this community's admin can reject requests.", "danger")
        return redirect(url_for("communities.communities_page"))

    reject_join_request(current_app.db, community_id, user_id)
    flash("Join request rejected.", "info")
    return redirect(url_for("communities.communities_page"))


@communities_bp.route("/create", methods=["POST"])
@login_required
def create():
    if current_user.role != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("communities.communities_page"))

    name = request.form.get("name", "").strip()
    location = request.form.get("location", "").strip()
    if not name or not location:
        flash("Name and location are required.", "warning")
        return redirect(url_for("communities.communities_page"))

    create_community(current_app.db, name, location, current_user.id)
    flash("Community created.", "success")
    return redirect(url_for("communities.communities_page"))


@communities_bp.route("/<community_id>/delete", methods=["POST"])
@login_required
def delete(community_id):
    if current_user.role != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("communities.communities_page"))

    delete_community(current_app.db, community_id)
    flash("Community deleted.", "info")
    return redirect(url_for("communities.communities_page"))
