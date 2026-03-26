from bson.objectid import ObjectId


def _communities(db):
    return db["communities"]


def _to_object_id(value: str):
    try:
        return ObjectId(value)
    except Exception:
        return None


def _sanitize_community_shape(db, community: dict):
    """Normalize legacy community docs so list/set operations are always safe."""
    updates = {}

    members = community.get("members", [])
    if not isinstance(members, list):
        updates["members"] = []
        members = []

    pending = community.get("pending_requests", [])
    if not isinstance(pending, list):
        updates["pending_requests"] = []
        pending = []

    admin_id = community.get("admin_id")
    if admin_id is not None and not isinstance(admin_id, str):
        updates["admin_id"] = None

    if updates:
        _communities(db).update_one({"_id": community["_id"]}, {"$set": updates})
        community.update(updates)

    community["members"] = members
    community["pending_requests"] = pending
    return community


def ensure_default_communities(db):
    if _communities(db).count_documents({}) > 0:
        return

    _communities(db).insert_many(
        [
            {
                "name": "Green Meadows",
                "location": "North Zone",
                "members": [],
                "pending_requests": [],
                "admin_id": None,
            },
            {
                "name": "Lakeside Heights",
                "location": "East Zone",
                "members": [],
                "pending_requests": [],
                "admin_id": None,
            },
            {
                "name": "Central Harmony",
                "location": "City Center",
                "members": [],
                "pending_requests": [],
                "admin_id": None,
            },
            {
                "name": "Sunrise Colony",
                "location": "South Zone",
                "members": [],
                "pending_requests": [],
                "admin_id": None,
            },
        ]
    )


def list_communities(db, search: str | None = None):
    query = {}
    if search:
        query = {"name": {"$regex": search, "$options": "i"}}
    communities = list(_communities(db).find(query).sort("name", 1))
    return [_sanitize_community_shape(db, community) for community in communities]


def get_community(db, community_id: str):
    oid = _to_object_id(community_id)
    if not oid:
        return None

    community = _communities(db).find_one({"_id": oid})
    if not community:
        return None
    return _sanitize_community_shape(db, community)


def request_to_join_community(db, community_id: str, user_id: str):
    community = get_community(db, community_id)
    if not community:
        return "not_found"

    if user_id in community.get("members", []):
        return "already_member"

    if user_id in community.get("pending_requests", []):
        return "already_requested"

    _communities(db).update_one(
        {"_id": community["_id"]},
        {"$addToSet": {"pending_requests": user_id}},
    )
    return "requested"


def approve_join_request(db, community_id: str, user_id: str):
    community = get_community(db, community_id)
    if not community:
        return False

    _communities(db).update_one(
        {"_id": community["_id"]},
        {
            "$pull": {"pending_requests": user_id},
            "$addToSet": {"members": user_id},
        },
    )
    return True


def reject_join_request(db, community_id: str, user_id: str):
    community = get_community(db, community_id)
    if not community:
        return False

    _communities(db).update_one(
        {"_id": community["_id"]},
        {"$pull": {"pending_requests": user_id}},
    )
    return True


def can_manage_community(community: dict, user_id: str, role: str):
    # Platform admins can manage all communities; community admins manage their own.
    return role == "admin" or community.get("admin_id") == user_id


def create_community(db, name: str, location: str, admin_id: str | None = None):
    return _communities(db).insert_one(
        {
            "name": name.strip(),
            "location": location.strip(),
            "members": [],
            "pending_requests": [],
            "admin_id": admin_id,
        }
    )


def delete_community(db, community_id: str):
    oid = _to_object_id(community_id)
    if not oid:
        return None
    return _communities(db).delete_one({"_id": oid})
