"""Bootstrap MongoDB collections and indexes for Assistly."""
from dotenv import load_dotenv
from pymongo import ASCENDING, DESCENDING

load_dotenv()

from config import get_db


COLLECTIONS = [
    "users",
    "requests",
    "communities",
    "community_invites",
    "community_messages",
    "admin_access_requests",
    "email_verifications",
    "volunteer_profiles",
    "volunteer_ratings",
    "conversations",
    "messages",
]


def ensure_collection(db, name: str):
    if name not in db.list_collection_names():
        db.create_collection(name)
        print(f"Created collection: {name}")
    else:
        print(f"Collection exists: {name}")


def ensure_indexes(db):
    # Core user/request/community lookups
    db["users"].create_index([("email", ASCENDING)], unique=True, sparse=True)
    db["users"].create_index([("role", ASCENDING), ("mode", ASCENDING)])

    db["requests"].create_index([("user_id", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)])
    db["requests"].create_index([("community_id", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)])
    db["requests"].create_index([("accepted_by", ASCENDING), ("status", ASCENDING), ("updated_at", DESCENDING)])
    db["requests"].create_index([("category", ASCENDING), ("status", ASCENDING)])
    db["requests"].create_index([("tags", ASCENDING)])

    db["communities"].create_index([("admin_id", ASCENDING)])
    db["communities"].create_index([("location", ASCENDING)])

    db["community_invites"].create_index([("community_id", ASCENDING), ("email", ASCENDING)], unique=True)
    db["community_messages"].create_index([("community_id", ASCENDING), ("created_at", DESCENDING)])
    db["admin_access_requests"].create_index([("community_id", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)])
    db["email_verifications"].create_index([("email", ASCENDING)], unique=True)

    db["volunteer_profiles"].create_index([("user_id", ASCENDING)], unique=True)
    db["volunteer_profiles"].create_index([("skills", ASCENDING)])
    db["volunteer_ratings"].create_index([("volunteer_id", ASCENDING), ("created_at", DESCENDING)])
    db["volunteer_ratings"].create_index([("request_id", ASCENDING)], unique=True)

    db["conversations"].create_index([("participants", ASCENDING)], unique=True)
    db["conversations"].create_index([("last_message_at", DESCENDING)])
    db["messages"].create_index([("conversation_id", ASCENDING), ("created_at", DESCENDING)])
    db["messages"].create_index([("recipient_id", ASCENDING), ("read", ASCENDING), ("created_at", DESCENDING)])


def main():
    db = get_db()
    print(f"Connected to database: {db.name}")

    for collection_name in COLLECTIONS:
        ensure_collection(db, collection_name)

    ensure_indexes(db)
    print("Bootstrap complete.")


if __name__ == "__main__":
    main()
