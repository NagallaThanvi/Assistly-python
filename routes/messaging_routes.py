"""Routes for direct messaging between users."""
from flask import Blueprint, current_app, jsonify, request, render_template, flash, redirect, url_for
from flask_login import current_user, login_required

from models.messaging_model import (
    send_message,
    get_user_conversations,
    get_conversation_messages,
    mark_messages_as_read,
    get_unread_message_count,
    delete_conversation,
)
from models.user_model import find_user_by_id, get_user_object_by_id


messaging_bp = Blueprint("messaging", __name__, url_prefix="/messaging")


@messaging_bp.route("/", methods=["GET"])
@login_required
def messages_page():
    """Display messages/conversations page."""
    conversations = get_user_conversations(current_app.db, current_user.id)
    unread_count = get_unread_message_count(current_app.db, current_user.id)
    
    # Enrich conversation data with user information
    enriched = []
    for conv in conversations:
        other_user_id = [u for u in conv["participants"] if u != current_user.id][0]
        other_user = get_user_object_by_id(current_app.db, other_user_id)
        
        enriched.append({
            "id": str(conv["_id"]),
            "other_user_id": other_user_id,
            "other_user_name": other_user.name if other_user else "Unknown",
            "last_message": conv.get("last_message", ""),
            "last_message_at": conv.get("last_message_at"),
            "unread": False,  # TODO: Track unread per conversation
        })
    
    return render_template(
        "messages.html",
        conversations=enriched,
        unread_count=unread_count,
    )


@messaging_bp.route("/conversation/<other_user_id>", methods=["GET"])
@login_required
def conversation_page(other_user_id):
    """Display conversation with a specific user."""
    # Verify user exists
    other_user = get_user_object_by_id(current_app.db, other_user_id)
    if not other_user:
        flash("User not found.", "warning")
        return redirect(url_for("messaging.messages_page"))
    
    # Get messages (this will also create conversation if needed)
    from models.messaging_model import get_or_create_conversation
    conversation = get_or_create_conversation(current_app.db, current_user.id, other_user_id)
    
    messages = get_conversation_messages(current_app.db, str(conversation["_id"]), limit=50)
    messages.reverse()  # Oldest first
    
    # Mark as read
    mark_messages_as_read(current_app.db, str(conversation["_id"]), current_user.id)
    
    return render_template(
        "conversation.html",
        other_user=other_user,
        other_user_id=other_user_id,
        conversation_id=str(conversation["_id"]),
        messages=messages,
    )


@messaging_bp.route("/send", methods=["POST"])
@login_required
def send_message_route():
    """Send a message to another user."""
    data = request.get_json() or {}
    
    recipient_id = data.get("recipient_id", "").strip()
    text = data.get("text", "").strip()
    
    if not recipient_id or not text:
        return jsonify({"ok": False, "reason": "Missing recipient or message"}), 400
    
    # Prevent sending to self
    if recipient_id == current_user.id:
        return jsonify({"ok": False, "reason": "Cannot message yourself"}), 400
    
    # Verify recipient exists
    recipient = get_user_object_by_id(current_app.db, recipient_id)
    if not recipient:
        return jsonify({"ok": False, "reason": "Recipient not found"}), 404
    
    result = send_message(current_app.db, current_user.id, recipient_id, text)
    
    return jsonify(result)


@messaging_bp.route("/conversation/<conversation_id>/delete", methods=["POST"])
@login_required
def delete_conversation_route(conversation_id):
    """Delete a conversation."""
    result = delete_conversation(current_app.db, conversation_id, current_user.id)
    
    if not result.get("ok"):
        return jsonify(result), 403
    
    flash("Conversation deleted.", "info")
    return redirect(url_for("messaging.messages_page"))


@messaging_bp.route("/unread-count", methods=["GET"])
@login_required
def unread_count():
    """Get unread message count."""
    count = get_unread_message_count(current_app.db, current_user.id)
    return jsonify({"unread_count": count})


@messaging_bp.route("/api/conversations", methods=["GET"])
@login_required
def conversations_api():
    """API endpoint for getting conversations."""
    conversations = get_user_conversations(current_app.db, current_user.id)
    
    enriched = []
    for conv in conversations:
        other_user_id = [u for u in conv["participants"] if u != current_user.id][0]
        other_user = get_user_object_by_id(current_app.db, other_user_id)
        
        enriched.append({
            "id": str(conv["_id"]),
            "other_user_id": other_user_id,
            "other_user_name": other_user.name if other_user else "Unknown",
            "last_message": conv.get("last_message"),
            "last_message_at": conv.get("last_message_at").isoformat() if conv.get("last_message_at") else None,
        })
    
    return jsonify({"conversations": enriched})
