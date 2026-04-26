"""Routes for analytics and insights dashboard."""
from flask import Blueprint, current_app, jsonify, render_template, request
from flask_login import current_user, login_required

from models.analytics_model import (
    get_platform_metrics,
    get_community_metrics,
    get_request_metrics_by_category,
    get_request_status_distribution,
    get_volunteer_leaderboard,
    get_daily_activity,
    get_user_insights,
)


analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@analytics_bp.route("/dashboard", methods=["GET"])
@login_required
def analytics_dashboard():
    """Display comprehensive analytics dashboard."""
    # Only admins and community leaders can view full analytics
    # For now, allow all authenticated users but show personalized data

    metrics = get_platform_metrics(current_app.db, days=30)
    category_metrics = get_request_metrics_by_category(current_app.db, days=30)
    status_distribution = get_request_status_distribution(current_app.db, days=30)
    leaderboard = get_volunteer_leaderboard(current_app.db, limit=10)
    daily_activity = get_daily_activity(current_app.db, days=30)
    user_insights = get_user_insights(current_app.db, current_user.id)
    atlas_charts = {
        "status_url": str(current_app.config.get("ATLAS_CHART_STATUS_URL", "") or "").strip(),
        "categories_url": str(current_app.config.get("ATLAS_CHART_CATEGORIES_URL", "") or "").strip(),
        "activity_url": str(current_app.config.get("ATLAS_CHART_ACTIVITY_URL", "") or "").strip(),
    }
    atlas_enabled = all(atlas_charts.values())
    
    return render_template(
        "analytics_dashboard.html",
        metrics=metrics,
        category_metrics=category_metrics,
        status_distribution=status_distribution,
        leaderboard=leaderboard,
        daily_activity=daily_activity,
        user_insights=user_insights,
        atlas_charts=atlas_charts,
        atlas_enabled=atlas_enabled,
    )


@analytics_bp.route("/api/metrics", methods=["GET"])
@login_required
def metrics_api():
    """API endpoint for metrics data."""
    days = request.args.get("days", 30, type=int)
    metrics = get_platform_metrics(current_app.db, days=days)
    return jsonify(metrics)


@analytics_bp.route("/api/category-metrics", methods=["GET"])
@login_required
def category_metrics_api():
    """API endpoint for category metrics."""
    days = request.args.get("days", 30, type=int)
    metrics = get_request_metrics_by_category(current_app.db, days=days)
    return jsonify({"metrics": metrics})


@analytics_bp.route("/api/status-distribution", methods=["GET"])
@login_required
def status_distribution_api():
    """API endpoint for request status distribution."""
    days = request.args.get("days", 30, type=int)
    distribution = get_request_status_distribution(current_app.db, days=days)
    return jsonify({"distribution": distribution})


@analytics_bp.route("/api/leaderboard", methods=["GET"])
@login_required
def leaderboard_api():
    """API endpoint for volunteer leaderboard."""
    limit = request.args.get("limit", 20, type=int)
    leaderboard = get_volunteer_leaderboard(current_app.db, limit=limit)
    return jsonify({"leaderboard": leaderboard})


@analytics_bp.route("/api/daily-activity", methods=["GET"])
@login_required
def daily_activity_api():
    """API endpoint for daily activity data."""
    days = request.args.get("days", 30, type=int)
    activity = get_daily_activity(current_app.db, days=days)
    return jsonify({"activity": activity})


@analytics_bp.route("/api/user-insights", methods=["GET"])
@login_required
def user_insights_api():
    """API endpoint for user's personal insights."""
    insights = get_user_insights(current_app.db, current_user.id)
    return jsonify(insights)


@analytics_bp.route("/community/<community_id>", methods=["GET"])
@login_required
def community_analytics(community_id):
    """View analytics for a specific community."""
    # TODO: Add community membership check
    metrics = get_community_metrics(current_app.db, community_id)
    
    return render_template(
        "community_analytics.html",
        community_id=community_id,
        metrics=metrics,
    )
