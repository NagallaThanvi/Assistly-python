"""Routes for volunteer ratings and reviews."""
from flask import Blueprint, current_app, jsonify, request, url_for, render_template, flash, redirect
from flask_login import current_user, login_required

from models.request_model import get_request_by_id, rate_request, confirm_request_completion
from models.volunteer_model import add_volunteer_rating, get_volunteer_profile_with_stats
from models.email_service import send_notification_email


ratings_bp = Blueprint("ratings", __name__, url_prefix="/ratings")


@ratings_bp.route("/request/<request_id>/rate", methods=["GET"])
@login_required
def rate_request_page(request_id):
    """Display rating form for a completed request."""
    req = get_request_by_id(current_app.db, request_id)
    
    if not req:
        flash("Request not found.", "warning")
        return redirect(url_for("dashboard.dashboard"))
    
    if req.get("user_id") != current_user.id:
        flash("You can only rate requests you created.", "warning")
        return redirect(url_for("dashboard.dashboard"))
    
    if req.get("status") != "Completed":
        flash("You can only rate completed requests.", "warning")
        return redirect(url_for("dashboard.dashboard"))
    
    return render_template(
        "rate_request.html",
        request_doc=req,
        volunteer_id=req.get("accepted_by"),
    )


@ratings_bp.route("/request/<request_id>/rate", methods=["POST"])
@login_required
def submit_rating(request_id):
    """Submit a rating and review for a completed request."""
    req = get_request_by_id(current_app.db, request_id)
    
    if not req or req.get("user_id") != current_user.id:
        return jsonify({"ok": False, "reason": "Unauthorized"}), 403
    
    if req.get("status") != "Completed":
        return jsonify({"ok": False, "reason": "Request not completed"}), 400
    
    try:
        rating = int(request.form.get("rating", 0))
        review = request.form.get("review", "").strip()
    except ValueError:
        return jsonify({"ok": False, "reason": "Invalid rating"}), 400
    
    if not 1 <= rating <= 5:
        return jsonify({"ok": False, "reason": "Rating must be between 1 and 5"}), 400
    
    # Submit rating for request
    result = rate_request(current_app.db, request_id, current_user.id, rating, review)
    
    if not result.get("ok"):
        return jsonify(result), 400
    
    # Also add to volunteer profile ratings
    volunteer_id = req.get("accepted_by")
    if volunteer_id:
        add_volunteer_rating(
            current_app.db,
            volunteer_id,
            request_id,
            rating,
            review,
            current_user.id,
        )
    
    flash("Thank you for rating this volunteer!", "success")
    return redirect(url_for("dashboard.dashboard"))


@ratings_bp.route("/request/<request_id>/confirm-complete", methods=["POST"])
@login_required
def confirm_completion(request_id):
    """Resident confirms that volunteer task is completed."""
    req = get_request_by_id(current_app.db, request_id)
    
    if not req or req.get("user_id") != current_user.id:
        return jsonify({"ok": False, "reason": "Unauthorized"}), 403
    
    if req.get("status") != "Completed":
        return jsonify({"ok": False, "reason": "Request not completed yet"}), 400
    
    result = confirm_request_completion(current_app.db, request_id, current_user.id)
    
    if result.modified_count == 0:
        return jsonify({"ok": False, "reason": "Could not confirm"}), 400
    
    flash("Thanks for confirming! Please rate the volunteer.", "success")
    return redirect(url_for("ratings.rate_request_page", request_id=request_id))


@ratings_bp.route("/volunteer/<volunteer_id>", methods=["GET"])
@login_required
def volunteer_profile(volunteer_id):
    """View volunteer profile with ratings and stats."""
    profile = get_volunteer_profile_with_stats(current_app.db, volunteer_id)
    
    if not profile:
        flash("Volunteer profile not found.", "warning")
        return redirect(url_for("dashboard.dashboard"))
    
    return render_template(
        "volunteer_profile.html",
        volunteer=profile,
        volunteer_id=volunteer_id,
    )
