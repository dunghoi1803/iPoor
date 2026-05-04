#!/usr/bin/env python3
"""Refresh dashboard aggregates script"""
import sys
sys.path.insert(0, "/app")

from app.database import SessionLocal
from app.routers.dashboard import ensure_dashboard_aggregates


def main():
    db = SessionLocal()
    try:
        print("Refreshing dashboard aggregates (force=True)...")
        latest_year = ensure_dashboard_aggregates(db, force=True)
        print(f"Done! Latest year: {latest_year}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()