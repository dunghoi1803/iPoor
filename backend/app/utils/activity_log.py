from sqlalchemy.orm import Session

from .. import models


def log_activity(
    db: Session,
    user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | None,
    detail: str | None = None,
    household_id: int | None = None,
    ip_address: str | None = None,
) -> None:
    log_entry = models.ActivityLog(
        user_id=user_id,
        household_id=household_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail,
        ip_address=ip_address,
    )
    db.add(log_entry)
