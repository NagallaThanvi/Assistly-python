"""Direct messaging system between residents and volunteers."""
from datetime import datetime
from bson.objectid import ObjectId


def _messages(db):
    return db["messages"]


def _conversations(db):
    return db["conversations"]


def get_or_create_conversation(db, user1_id: str, user2_id: str):
    """Get or create a conversation between two users."""
    # Ensure consistent ordering
    participants = sorted([user1_id, user2_id])
    
    conversation = _conversations(db).find_one({
        "participants": participants
    })
    
    if not conversation:
        conversation_doc = {
            "participants": participants,
            "user_ids": {user1_id, user2_id},
            "last_message": None,
            "last_message_at": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        result = _conversations(db).insert_one(conversation_doc)
        conversation = _conversations(db).find_one({"_id": result.inserted_id})
    
    return conversation


def send_message(db, sender_id: str, recipient_id: str, text: str):
    """Send a message between two users."""
    text = text.strip()
    if not text or len(text) > 5000:
        return {"ok": False, "reason": "Message must be between 1 and 5000 characters"}
    
    conversation = get_or_create_conversation(db, sender_id, recipient_id)
    
    message_doc = {
        "conversation_id": str(conversation["_id"]),
        "sender_id": sender_id,
        "recipient_id": recipient_id,
        "text": text,
        "read": False,
        "created_at": datetime.utcnow(),
    }
    
    result = _messages(db).insert_one(message_doc)
    
    # Update conversation
    _conversations(db).update_one(
        {"_id": conversation["_id"]},
        {
            "$set": {
                "last_message": text,
                "last_message_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        },
    )
    
    return {"ok": True, "message_id": str(result.inserted_id)}


def get_conversation_messages(db, conversation_id: str, limit: int = 50):
    """Get messages from a conversation."""
    try:
        return list(
            _messages(db)
            .find({"conversation_id": conversation_id})
            .sort("created_at", -1)
            .limit(limit)
        )
    except Exception:
        return []


def get_user_conversations(db, user_id: str):
    """Get all conversations for a user, ordered by most recent."""
    return list(
        _conversations(db)
        .find({"participants": {"$in": [user_id]}})
        .sort("last_message_at", -1)
    )


def mark_messages_as_read(db, conversation_id: str, user_id: str):
    """Mark all unread messages in a conversation as read."""
    return _messages(db).update_many(
        {
            "conversation_id": conversation_id,
            "recipient_id": user_id,
            "read": False,
        },
        {"$set": {"read": True}},
    )


def get_unread_message_count(db, user_id: str):
    """Get count of unread messages for a user."""
    return _messages(db).count_documents({
        "recipient_id": user_id,
        "read": False,
    })


def delete_conversation(db, conversation_id: str, user_id: str):
    """Delete a conversation for a user."""
    conversation = _conversations(db).find_one({"_id": ObjectId(conversation_id)})
    
    if not conversation or user_id not in conversation.get("participants", []):
        return {"ok": False, "reason": "Unauthorized"}
    
    # Delete all messages in this conversation
    _messages(db).delete_many({"conversation_id": conversation_id})
    
    # Delete conversation
    _conversations(db).delete_one({"_id": ObjectId(conversation_id)})
    
    return {"ok": True}
