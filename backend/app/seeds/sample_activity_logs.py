"""Seed sample activity logs into the database."""

from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models import ActivityLog, Household, Policy, User


ACTION_CREATE_HOUSEHOLD = "create_household"
ACTION_UPDATE_HOUSEHOLD = "update_household"
ACTION_DELETE_HOUSEHOLD = "delete_household"
ACTION_CREATE_POLICY = "create_policy"
ACTION_UPDATE_POLICY = "update_policy"
ACTION_DELETE_POLICY = "delete_policy"
ACTION_UPLOAD_FILE = "upload_policy_attachment"
ACTION_VIEW_HOUSEHOLD = "view_household"

ENTITY_HOUSEHOLD = "household"
ENTITY_POLICY = "policy"

DEFAULT_IP = "127.0.0.1"
ALT_IP = "10.20.30.40"

SAMPLES = [
    {"user_email": "admin@ipoor.local", "action": ACTION_CREATE_HOUSEHOLD, "entity": "household", "offset": 1},
    {"user_email": "admin@ipoor.local", "action": ACTION_UPDATE_HOUSEHOLD, "entity": "household", "offset": 2},
    {"user_email": "admin@ipoor.local", "action": ACTION_DELETE_HOUSEHOLD, "entity": "household", "offset": 3},
    {"user_email": "canbo.tinh@ipoor.local", "action": ACTION_CREATE_POLICY, "entity": "policy", "offset": 1},
    {"user_email": "canbo.tinh@ipoor.local", "action": ACTION_UPDATE_POLICY, "entity": "policy", "offset": 2},
    {"user_email": "canbo.tinh@ipoor.local", "action": ACTION_UPLOAD_FILE, "entity": "policy", "offset": 2},
    {"user_email": "canbo.huyen@ipoor.local", "action": ACTION_CREATE_HOUSEHOLD, "entity": "household", "offset": 4},
    {"user_email": "canbo.huyen@ipoor.local", "action": ACTION_VIEW_HOUSEHOLD, "entity": "household", "offset": 4},
    {"user_email": "canbo.huyen@ipoor.local", "action": ACTION_UPDATE_HOUSEHOLD, "entity": "household", "offset": 5},
    {"user_email": "canbo.xa@ipoor.local", "action": ACTION_UPDATE_HOUSEHOLD, "entity": "household", "offset": 6},
    {"user_email": "canbo.xa@ipoor.local", "action": ACTION_VIEW_HOUSEHOLD, "entity": "household", "offset": 6},
    {"user_email": "admin@ipoor.local", "action": ACTION_UPDATE_POLICY, "entity": "policy", "offset": 4},
    {"user_email": "admin@ipoor.local", "action": ACTION_DELETE_POLICY, "entity": "policy", "offset": 5},
    {"user_email": "canbo.tinh@ipoor.local", "action": ACTION_CREATE_POLICY, "entity": "policy", "offset": 6},
    {"user_email": "canbo.tinh@ipoor.local", "action": ACTION_UPLOAD_FILE, "entity": "policy", "offset": 7},
    {"user_email": "canbo.huyen@ipoor.local", "action": ACTION_CREATE_HOUSEHOLD, "entity": "household", "offset": 7},
    {"user_email": "canbo.huyen@ipoor.local", "action": ACTION_UPDATE_HOUSEHOLD, "entity": "household", "offset": 8},
    {"user_email": "canbo.xa@ipoor.local", "action": ACTION_CREATE_HOUSEHOLD, "entity": "household", "offset": 9},
    {"user_email": "canbo.xa@ipoor.local", "action": ACTION_VIEW_HOUSEHOLD, "entity": "household", "offset": 9},
    {"user_email": "admin@ipoor.local", "action": ACTION_UPDATE_POLICY, "entity": "policy", "offset": 10},
]


def pick_entity_id(items: list, index: int) -> int | None:
    if not items:
        return None
    safe_index = min(index, len(items) - 1)
    return items[safe_index].id


def seed_activity_logs() -> None:
    db = SessionLocal()
    try:
        db.query(ActivityLog).delete()
        users = {user.email: user for user in db.query(User).all()}
        households = db.query(Household).order_by(Household.id).all()
        policies = db.query(Policy).order_by(Policy.id).all()
        now = datetime.utcnow()
        for idx, item in enumerate(SAMPLES):
            user = users.get(item["user_email"])
            entity_type = ENTITY_HOUSEHOLD if item["entity"] == "household" else ENTITY_POLICY
            entity_id = (
                pick_entity_id(households, idx) if entity_type == ENTITY_HOUSEHOLD else pick_entity_id(policies, idx)
            )
            household_id = entity_id if entity_type == ENTITY_HOUSEHOLD else None
            ip_address = DEFAULT_IP if idx % 2 == 0 else ALT_IP
            created_at = now - timedelta(days=item["offset"])
            log = ActivityLog(
                user_id=user.id if user else None,
                household_id=household_id,
                action=item["action"],
                entity_type=entity_type,
                entity_id=entity_id,
                detail="Seeded activity",
                ip_address=ip_address,
                created_at=created_at,
            )
            db.add(log)
        db.commit()
        print("Inserted sample activity logs.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_activity_logs()
