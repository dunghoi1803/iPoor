"""Seed all tables with sample data."""

from app.database import SessionLocal
from app.models import ActivityLog, Household, Policy, PolicyDraft, User
from app.seeds.sample_activity_logs import seed_activity_logs
from app.seeds.sample_households import seed_households
from app.seeds.sample_policies import seed_policies
from app.seeds.sample_users import seed_users


def reset_tables() -> None:
    db = SessionLocal()
    try:
        db.query(ActivityLog).delete()
        db.query(PolicyDraft).delete()
        db.query(Policy).delete()
        db.query(Household).delete()
        db.query(User).delete()
        db.commit()
    finally:
        db.close()


def seed_all() -> None:
    reset_tables()
    seed_users()
    seed_households()
    seed_policies()
    seed_activity_logs()
    print("Seeded users, households, policies, and activity logs.")


if __name__ == "__main__":
    seed_all()
