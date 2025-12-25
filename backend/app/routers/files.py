import uuid
from pathlib import Path
from urllib.parse import quote

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from ..config import get_settings
from ..deps import get_current_user
from ..utils.file_naming import (
    FILENAME_MAX_LENGTH,
    FILENAME_SEPARATOR,
    build_household_prefix,
    slugify_filename,
    translate_policy_category,
)

router = APIRouter(prefix="/files", tags=["files"])

settings = get_settings()
UPLOAD_DIR = Path(settings.upload_dir)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_CHUNK_SIZE = 1024 * 1024
EDITOR_IMAGE_MAX_SIZE_BYTES = 5 * 1024 * 1024
ENTITY_POLICY = "policy"
ENTITY_HOUSEHOLD = "household"
ALLOWED_ENTITIES = {ENTITY_POLICY, ENTITY_HOUSEHOLD}
HOUSEHOLD_SUBDIR = "households"
POLICY_ATTACHMENTS_SUBDIR = "policies/attachments"
POLICY_CONTENT_SUBDIR = "policies/content"
ALLOWED_EDITOR_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
ALLOWED_POLICY_ATTACHMENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/png",
    "image/jpeg",
}
ALLOWED_HOUSEHOLD_ATTACHMENT_TYPES = {"application/pdf", "image/png", "image/jpeg"}
DRAFT_ATTACHMENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
DRAFTS_SUBDIR = "drafts"
DRAFTS_POLICY_IMAGES_SUBDIR = "policies/images"
DRAFTS_POLICY_ATTACHMENTS_SUBDIR = "policies/attachments"


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),  # noqa: B008
    entity_type: str = Form(ENTITY_POLICY),
    policy_category: str | None = Form(None),
    household_code: str | None = Form(None),
    poverty_status: str | None = Form(None),
    head_name: str | None = Form(None),
    id_card: str | None = Form(None),
    current_user=Depends(get_current_user),
):
    normalized_entity = (entity_type or ENTITY_POLICY).strip().lower()
    if normalized_entity not in ALLOWED_ENTITIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid entity type",
        )
    if normalized_entity == ENTITY_HOUSEHOLD:
        allowed_types = ALLOWED_HOUSEHOLD_ATTACHMENT_TYPES
        error_message = "Only PDF or image files are allowed"
    else:
        allowed_types = ALLOWED_POLICY_ATTACHMENT_TYPES
        error_message = "Only PDF, Word, or image files are allowed"
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message,
        )
    subdir = HOUSEHOLD_SUBDIR if normalized_entity == ENTITY_HOUSEHOLD else POLICY_ATTACHMENTS_SUBDIR
    target_dir = UPLOAD_DIR / subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    extension = Path(file.filename).suffix or ""
    random_suffix = uuid.uuid4().hex
    if normalized_entity == ENTITY_HOUSEHOLD:
        prefix = build_household_prefix(household_code, poverty_status, head_name, id_card)
        raw_name = f"{prefix}{extension}" if prefix else f"{random_suffix}{extension}"
    else:
        category_label = translate_policy_category(policy_category)
        category_slug = slugify_filename(category_label)
        prefix = category_slug or ""
        raw_name = f"{prefix}{FILENAME_SEPARATOR}{random_suffix}{extension}" if prefix else f"{random_suffix}{extension}"
    safe_name = raw_name[:FILENAME_MAX_LENGTH]
    file_path = target_dir / safe_name
    if normalized_entity == ENTITY_HOUSEHOLD:
        counter = 1
        stem = Path(safe_name).stem
        while file_path.exists():
            candidate = f"{stem}{FILENAME_SEPARATOR}{counter}{extension}"
            safe_name = candidate[:FILENAME_MAX_LENGTH]
            file_path = target_dir / safe_name
            counter += 1
    async with aiofiles.open(file_path, "wb") as out_file:
        while True:
            chunk = await file.read(UPLOAD_CHUNK_SIZE)
            if not chunk:
                break
            await out_file.write(chunk)
    encoded_name = quote(safe_name)
    return JSONResponse(
        {
            "url": f"/files/{subdir}/{encoded_name}",
            "filename": file.filename,
            "stored_as": safe_name,
        }
    )


@router.post("/upload-article")
async def upload_article_image(
    file: UploadFile = File(...),  # noqa: B008
    current_user=Depends(get_current_user),
):
    if file.content_type not in ALLOWED_EDITOR_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PNG, JPG, or WEBP images are allowed",
        )
    target_dir = UPLOAD_DIR / POLICY_CONTENT_SUBDIR
    target_dir.mkdir(parents=True, exist_ok=True)
    extension = Path(file.filename).suffix or ""
    safe_name = f"{uuid.uuid4().hex}{extension}"
    file_path = target_dir / safe_name
    total_size = 0
    async with aiofiles.open(file_path, "wb") as out_file:
        while True:
            chunk = await file.read(UPLOAD_CHUNK_SIZE)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > EDITOR_IMAGE_MAX_SIZE_BYTES:
                await out_file.close()
                if file_path.exists():
                    file_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Image exceeds size limit",
                )
            await out_file.write(chunk)
    encoded_name = quote(safe_name)
    return JSONResponse(
        {
            "success": 1,
            "file": {"url": f"/files/{POLICY_CONTENT_SUBDIR}/{encoded_name}"},
        }
    )


@router.post("/upload-draft")
async def upload_draft_file(
    file: UploadFile = File(...),  # noqa: B008
    purpose: str = Form("image"),
    current_user=Depends(get_current_user),
):
    normalized = (purpose or "image").strip().lower()
    if normalized == "image":
        if file.content_type not in ALLOWED_EDITOR_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PNG, JPG, or WEBP images are allowed",
            )
    elif normalized == "attachment":
        if file.content_type not in DRAFT_ATTACHMENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF or Word files are allowed",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid draft file purpose",
        )
    target_subdir = DRAFTS_POLICY_IMAGES_SUBDIR if normalized == "image" else DRAFTS_POLICY_ATTACHMENTS_SUBDIR
    target_dir = UPLOAD_DIR / DRAFTS_SUBDIR / str(current_user.id) / target_subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    extension = Path(file.filename).suffix or ""
    safe_name = f"{uuid.uuid4().hex}{extension}"
    file_path = target_dir / safe_name
    async with aiofiles.open(file_path, "wb") as out_file:
        while True:
            chunk = await file.read(UPLOAD_CHUNK_SIZE)
            if not chunk:
                break
            await out_file.write(chunk)
    encoded_name = quote(safe_name)
    url = f"/files/{DRAFTS_SUBDIR}/{current_user.id}/{target_subdir}/{encoded_name}"
    if normalized == "image":
        return JSONResponse({"success": 1, "file": {"url": url}})
    return JSONResponse(
        {
            "url": url,
            "filename": file.filename,
            "stored_as": safe_name,
        }
    )
