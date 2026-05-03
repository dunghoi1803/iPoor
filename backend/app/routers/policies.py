from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from .. import deps, models, schemas
from ..constants import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, PolicyCategory
from ..config import get_settings
from ..utils.activity_log import log_activity

router = APIRouter(prefix="/policies", tags=["policies"])
CATEGORY_GROUPS = {
    "policy": {PolicyCategory.DECREE, PolicyCategory.CIRCULAR},
    "guide": {PolicyCategory.GUIDELINE},
}
DRAFT_RETENTION_DAYS = 30
DRAFT_DEFAULT_LIMIT = DEFAULT_PAGE_LIMIT
DRAFT_MAX_LIMIT = 50
settings = get_settings()


def sanitize_attachment_files(items: list[dict] | None) -> list[dict] | None:
    if not isinstance(items, list):
        return items
    cleaned: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        raw_url = item.get("url")
        raw_name = item.get("name")
        url = raw_url.strip() if isinstance(raw_url, str) else ""
        name = raw_name.strip() if isinstance(raw_name, str) else ""
        if not url or not name:
            continue
        cleaned.append({"url": url, "name": name})
    return cleaned


def extract_draft_file_urls(draft: models.PolicyDraft) -> set[str]:
    urls: set[str] = set()
    for item in draft.attachment_files or []:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if isinstance(url, str) and url.startswith("/files/drafts/"):
            urls.add(url)
    blocks = draft.content_blocks or {}
    for block in blocks.get("blocks", []):
        if not isinstance(block, dict):
            continue
        if block.get("type") != "image":
            continue
        file_data = (block.get("data") or {}).get("file") or {}
        url = file_data.get("url")
        if isinstance(url, str) and url.startswith("/files/drafts/"):
            urls.add(url)
    return urls


def cleanup_old_drafts(db: Session) -> None:
    cutoff = datetime.utcnow() - timedelta(days=DRAFT_RETENTION_DAYS)
    old_drafts = db.query(models.PolicyDraft).filter(models.PolicyDraft.updated_at < cutoff).all()
    if not old_drafts:
        return
    upload_root = Path(settings.upload_dir)
    for draft in old_drafts:
        for url in extract_draft_file_urls(draft):
            relative_path = url.replace("/files/", "").lstrip("/")
            file_path = upload_root / relative_path
            if file_path.exists():
                file_path.unlink(missing_ok=True)
    for draft in old_drafts:
        db.delete(draft)
    db.commit()


@router.get("", response_model=list[schemas.PolicyRead])
def list_policies(
    category: PolicyCategory | None = None,
    skip: int = 0,
    limit: int = Query(DEFAULT_PAGE_LIMIT, le=MAX_PAGE_LIMIT),
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> list[models.Policy]:
    query = db.query(models.Policy)
    if category:
        query = query.filter(models.Policy.category == category)
    return query.offset(skip).limit(limit).all()


@router.get("/public", response_model=list[schemas.PolicyRead])
def list_public_policies(
    category: PolicyCategory | None = None,
    category_group: str | None = None,
    q: str | None = Query(None, min_length=1),
    skip: int = 0,
    limit: int = Query(DEFAULT_PAGE_LIMIT, le=MAX_PAGE_LIMIT),
    db: Session = Depends(deps.get_db),
) -> list[models.Policy]:
    query = db.query(models.Policy).filter(models.Policy.is_public.is_(True))
    if category_group:
        group = CATEGORY_GROUPS.get(category_group.strip().lower())
        if group:
            query = query.filter(models.Policy.category.in_(group))
    elif category:
        query = query.filter(models.Policy.category == category)
    if q:
        keyword = f"%{q.strip()}%"
        query = query.filter(
            or_(
                models.Policy.title.ilike(keyword),
                models.Policy.summary.ilike(keyword),
                models.Policy.description.ilike(keyword),
                models.Policy.issued_by.ilike(keyword),
            )
        )
    return query.order_by(models.Policy.updated_at.desc(), models.Policy.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/public/brief", response_model=list[schemas.PolicyBrief])
def list_public_policy_brief(
    limit: int = Query(7, le=MAX_PAGE_LIMIT),
    db: Session = Depends(deps.get_db),
) -> list[schemas.PolicyBrief]:
    rows = (
        db.query(
            models.Policy.id,
            models.Policy.title,
            models.Policy.summary,
            models.Policy.description,
            models.Policy.category,
            models.Policy.created_at,
            models.Policy.updated_at,
        )
        .filter(models.Policy.is_public.is_(True))
        .order_by(models.Policy.updated_at.desc(), models.Policy.created_at.desc())
        .limit(limit)
        .all()
    )
    return [schemas.PolicyBrief(**dict(row._mapping)) for row in rows]


@router.get("/public/{policy_id}", response_model=schemas.PolicyRead)
def get_public_policy(
    policy_id: int,
    db: Session = Depends(deps.get_db),
) -> models.Policy:
    policy = (
        db.query(models.Policy)
        .filter(models.Policy.id == policy_id, models.Policy.is_public.is_(True))
        .first()
    )
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return policy


@router.post("", response_model=schemas.PolicyRead, status_code=status.HTTP_201_CREATED)
def create_policy(
    payload: schemas.PolicyCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    request: Request = None,
) -> models.Policy:
    data = payload.model_dump()
    data["attachment_files"] = sanitize_attachment_files(data.get("attachment_files"))
    policy = models.Policy(**data)
    db.add(policy)
    db.flush()
    log_activity(
        db,
        user_id=current_user.id,
        action="create_policy",
        entity_type="policy",
        entity_id=policy.id,
        detail="Policy created",
        ip_address=request.client.host if request else None,
    )
    db.commit()
    db.refresh(policy)
    return policy


@router.get("/drafts/current", response_model=schemas.PolicyDraftRead)
def get_current_draft(
    policy_id: int | None = None,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> models.PolicyDraft:
    query = db.query(models.PolicyDraft).filter(models.PolicyDraft.user_id == current_user.id)
    if policy_id is None:
        query = query.filter(models.PolicyDraft.policy_id.is_(None))
    else:
        query = query.filter(models.PolicyDraft.policy_id == policy_id)
    draft = query.order_by(models.PolicyDraft.updated_at.desc(), models.PolicyDraft.created_at.desc()).first()
    if not draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    return draft


@router.get("/drafts", response_model=list[schemas.PolicyDraftRead])
def list_drafts(
    policy_id: int | None = None,
    only_unlinked: bool = False,
    limit: int = Query(DRAFT_DEFAULT_LIMIT, le=DRAFT_MAX_LIMIT),
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> list[models.PolicyDraft]:
    query = db.query(models.PolicyDraft).filter(models.PolicyDraft.user_id == current_user.id)
    if only_unlinked:
        query = query.filter(models.PolicyDraft.policy_id.is_(None))
    elif policy_id is not None:
        query = query.filter(models.PolicyDraft.policy_id == policy_id)
    return (
        query.order_by(models.PolicyDraft.updated_at.desc(), models.PolicyDraft.created_at.desc())
        .limit(limit)
        .all()
    )


@router.post("/drafts", response_model=schemas.PolicyDraftRead)
def upsert_draft(
    payload: schemas.PolicyDraftUpsert,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> models.PolicyDraft:
    cleanup_old_drafts(db)
    query = db.query(models.PolicyDraft).filter(models.PolicyDraft.user_id == current_user.id)
    if payload.policy_id is None:
        query = query.filter(models.PolicyDraft.policy_id.is_(None))
    else:
        query = query.filter(models.PolicyDraft.policy_id == payload.policy_id)
    draft = query.first()
    if draft:
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(draft, key, value)
    else:
        draft = models.PolicyDraft(user_id=current_user.id, **payload.model_dump())
        db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


@router.delete("/drafts/current", status_code=status.HTTP_204_NO_CONTENT)
def delete_current_draft(
    policy_id: int | None = None,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> None:
    query = db.query(models.PolicyDraft).filter(models.PolicyDraft.user_id == current_user.id)
    if policy_id is None:
        query = query.filter(models.PolicyDraft.policy_id.is_(None))
    else:
        query = query.filter(models.PolicyDraft.policy_id == policy_id)
    draft = query.order_by(models.PolicyDraft.updated_at.desc(), models.PolicyDraft.created_at.desc()).first()
    if not draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    upload_root = Path(settings.upload_dir)
    for url in extract_draft_file_urls(draft):
        relative_path = url.replace("/files/", "").lstrip("/")
        file_path = upload_root / relative_path
        if file_path.exists():
            file_path.unlink(missing_ok=True)
    db.delete(draft)
    db.commit()


@router.delete("/drafts/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_draft_by_id(
    draft_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> None:
    draft = (
        db.query(models.PolicyDraft)
        .filter(models.PolicyDraft.id == draft_id, models.PolicyDraft.user_id == current_user.id)
        .first()
    )
    if not draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    upload_root = Path(settings.upload_dir)
    for url in extract_draft_file_urls(draft):
        relative_path = url.replace("/files/", "").lstrip("/")
        file_path = upload_root / relative_path
        if file_path.exists():
            file_path.unlink(missing_ok=True)
    db.delete(draft)
    db.commit()


@router.get("/{policy_id}", response_model=schemas.PolicyRead)
def get_policy(
    policy_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> models.Policy:
    policy = db.query(models.Policy).filter(models.Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return policy


@router.put("/{policy_id}", response_model=schemas.PolicyRead)
def update_policy(
    policy_id: int,
    payload: schemas.PolicyUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    request: Request = None,
) -> models.Policy:
    policy = db.query(models.Policy).filter(models.Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    update_data = payload.model_dump(exclude_unset=True)
    if "attachment_files" in update_data:
        update_data["attachment_files"] = sanitize_attachment_files(update_data.get("attachment_files"))
    for key, value in update_data.items():
        setattr(policy, key, value)
    log_activity(
        db,
        user_id=current_user.id,
        action="update_policy",
        entity_type="policy",
        entity_id=policy.id,
        detail="Policy updated",
        ip_address=request.client.host if request else None,
    )
    db.commit()
    db.refresh(policy)
    return policy


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy(
    policy_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    request: Request = None,
) -> None:
    policy = db.query(models.Policy).filter(models.Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    db.query(models.PolicyDraft).filter(models.PolicyDraft.policy_id == policy_id).update(
        {models.PolicyDraft.policy_id: None}
    )
    log_activity(
        db,
        user_id=current_user.id,
        action="delete_policy",
        entity_type="policy",
        entity_id=policy.id,
        detail="Policy removed",
        ip_address=request.client.host if request else None,
    )
    db.delete(policy)
    db.commit()
