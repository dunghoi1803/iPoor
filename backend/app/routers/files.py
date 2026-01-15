import subprocess
import uuid
from pathlib import Path
from urllib.parse import quote

import aiofiles
import boto3
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool

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
USER_UPLOAD_SUBDIR = "users"
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
PDF_COMPRESSION_PRESET = "printer"

S3_ENTITY_POLICY = "policy"
S3_ENTITY_HOUSEHOLD = "household"
S3_PURPOSE_ATTACHMENT = "attachment"
S3_PURPOSE_DRAFT_ATTACHMENT = "draft_attachment"
S3_PURPOSE_USER_CCCD = "user_cccd"
S3_ALLOWED_PURPOSES = {S3_PURPOSE_ATTACHMENT, S3_PURPOSE_DRAFT_ATTACHMENT, S3_PURPOSE_USER_CCCD}


class PresignRequest(BaseModel):
    filename: str
    content_type: str
    entity_type: str = ENTITY_POLICY
    purpose: str = S3_PURPOSE_ATTACHMENT
    policy_category: str | None = None
    household_code: str | None = None
    poverty_status: str | None = None
    head_name: str | None = None
    id_card: str | None = None
    user_full_name: str | None = None
    user_cccd: str | None = None


def get_s3_client():
    if not settings.s3_bucket or not settings.s3_region:
        return None
    if not settings.s3_access_key_id or not settings.s3_secret_access_key:
        return None
    return boto3.client(
        "s3",
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        endpoint_url=settings.s3_endpoint_url or None,
    )


def build_s3_key(
    filename: str,
    entity_type: str,
    purpose: str,
    policy_category: str | None,
    household_code: str | None,
    poverty_status: str | None,
    head_name: str | None,
    id_card: str | None,
    user_full_name: str | None,
    user_cccd: str | None,
    user_id: int | None,
) -> tuple[str, str]:
    extension = Path(filename).suffix or ""
    random_suffix = uuid.uuid4().hex
    normalized_entity = (entity_type or ENTITY_POLICY).strip().lower()
    if purpose == S3_PURPOSE_USER_CCCD:
        safe_cccd = slugify_filename(user_cccd or "")
        safe_name = slugify_filename(user_full_name or "")
        prefix_parts = [part for part in ["cccd", safe_cccd, safe_name] if part]
        raw_name = f"{FILENAME_SEPARATOR.join(prefix_parts)}{extension or '.png'}"
        subdir = USER_UPLOAD_SUBDIR
    elif normalized_entity == ENTITY_HOUSEHOLD:
        if normalized_entity not in ALLOWED_ENTITIES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid entity type")
        prefix = build_household_prefix(household_code, poverty_status, head_name, id_card)
        raw_name = f"{prefix}{extension}" if prefix else f"{random_suffix}{extension}"
        subdir = HOUSEHOLD_SUBDIR
    else:
        if normalized_entity not in ALLOWED_ENTITIES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid entity type")
        category_label = translate_policy_category(policy_category)
        category_slug = slugify_filename(category_label)
        prefix = category_slug or ""
        raw_name = f"{prefix}{FILENAME_SEPARATOR}{random_suffix}{extension}" if prefix else f"{random_suffix}{extension}"
        subdir = POLICY_ATTACHMENTS_SUBDIR

    if purpose == S3_PURPOSE_DRAFT_ATTACHMENT:
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing draft owner")
        subdir = f"{DRAFTS_SUBDIR}/{user_id}/{DRAFTS_POLICY_ATTACHMENTS_SUBDIR}"
    safe_name = raw_name[:FILENAME_MAX_LENGTH]
    return subdir, safe_name


def build_public_file_url(bucket: str, key: str) -> str:
    if settings.s3_public_base_url:
        return f"{settings.s3_public_base_url.rstrip('/')}/{key}"
    if settings.s3_endpoint_url:
        return f"{settings.s3_endpoint_url.rstrip('/')}/{bucket}/{key}"
    return f"https://{bucket}.s3.{settings.s3_region}.amazonaws.com/{key}"


def compress_pdf_inplace(file_path: Path) -> None:
    if not file_path.exists():
        return
    tmp_path = file_path.with_suffix(f"{file_path.suffix}.compressed")
    cmd = [
        "gs",
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS=/{PDF_COMPRESSION_PRESET}",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={tmp_path}",
        str(file_path),
    ]
    try:
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    except FileNotFoundError:
        return
    if result.returncode != 0 or not tmp_path.exists():
        tmp_path.unlink(missing_ok=True)
        return
    try:
        if tmp_path.stat().st_size < file_path.stat().st_size:
            tmp_path.replace(file_path)
        else:
            tmp_path.unlink(missing_ok=True)
    except OSError:
        tmp_path.unlink(missing_ok=True)


@router.post("/presign")
async def presign_upload(
    payload: PresignRequest,
    current_user=Depends(get_current_user),
):
    normalized_purpose = (payload.purpose or S3_PURPOSE_ATTACHMENT).strip().lower()
    if normalized_purpose not in S3_ALLOWED_PURPOSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid upload purpose")
    if normalized_purpose == S3_PURPOSE_USER_CCCD and payload.content_type != "image/png":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PNG files are allowed")
    s3_client = get_s3_client()
    if not s3_client:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="S3 is not configured")
    subdir, safe_name = build_s3_key(
        payload.filename,
        payload.entity_type,
        normalized_purpose,
        payload.policy_category,
        payload.household_code,
        payload.poverty_status,
        payload.head_name,
        payload.id_card,
        payload.user_full_name,
        payload.user_cccd,
        current_user.id,
    )
    key = f"{subdir}/{safe_name}"
    try:
        upload_url = s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.s3_bucket,
                "Key": key,
                "ContentType": payload.content_type,
            },
            ExpiresIn=settings.s3_presign_expires,
            HttpMethod="PUT",
        )
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to presign upload")
    file_url = build_public_file_url(settings.s3_bucket, key)
    return JSONResponse({"upload_url": upload_url, "file_url": file_url, "key": key})


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
    if file.content_type == "application/pdf":
        await run_in_threadpool(compress_pdf_inplace, file_path)
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
    if normalized == "attachment" and file.content_type == "application/pdf":
        await run_in_threadpool(compress_pdf_inplace, file_path)
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
