from datetime import date, datetime, time

from fastapi import APIRouter, Depends, Query
from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session

from .. import deps, models, schemas
from ..constants import DEFAULT_PAGE_LIMIT

router = APIRouter(prefix="/activity-logs", tags=["activity_logs"])
ACTIVITY_LOG_DEFAULT_LIMIT = 50
ACTIVITY_LOG_MAX_LIMIT = 50


@router.get("", response_model=list[schemas.ActivityLogRead])
def list_activity_logs(
    skip: int = 0,
    q: str | None = Query(None, min_length=1),
    action: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(ACTIVITY_LOG_DEFAULT_LIMIT, le=ACTIVITY_LOG_MAX_LIMIT),
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> list[models.ActivityLog]:
    query = (
        db.query(models.ActivityLog, models.User)
        .outerjoin(models.User, models.User.id == models.ActivityLog.user_id)
    )
    if q:
        keyword = f"%{q.strip()}%"
        query = query.filter(
            or_(
                models.User.email.ilike(keyword),
                models.User.full_name.ilike(keyword),
                cast(models.ActivityLog.user_id, String).ilike(keyword),
                models.ActivityLog.action.ilike(keyword),
                models.ActivityLog.entity_type.ilike(keyword),
            )
        )
    if action and action != "all":
        action_value = action.strip().lower()
        if action_value in {"create", "update", "delete", "view"}:
            query = query.filter(models.ActivityLog.action.ilike(f"{action_value}%"))
        elif action_value == "post":
            query = query.filter(models.ActivityLog.action.ilike("%policy%"))
        elif action_value == "upload":
            query = query.filter(models.ActivityLog.action.ilike("%upload%"))
        else:
            query = query.filter(models.ActivityLog.action == action_value)
    if date_from:
        query = query.filter(models.ActivityLog.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        query = query.filter(models.ActivityLog.created_at <= datetime.combine(date_to, time.max))
    logs = (
        query.order_by(models.ActivityLog.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    items: list[schemas.ActivityLogRead] = []
    for log, user in logs:
        items.append(
            schemas.ActivityLogRead(
                id=log.id,
                user_id=log.user_id,
                user_email=user.email if user else None,
                user_role=user.role if user else None,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                detail=log.detail,
                household_id=log.household_id,
                ip_address=log.ip_address,
                created_at=log.created_at,
            )
        )
    return items


@router.post("", response_model=schemas.ActivityLogRead)
def create_activity_log(
    payload: schemas.ActivityLogCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> models.ActivityLog:
    log_entry = models.ActivityLog(**payload.model_dump())
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry
