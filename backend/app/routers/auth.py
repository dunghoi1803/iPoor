from pathlib import Path
from urllib.parse import quote

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import EmailStr
from sqlalchemy.orm import Session

from .. import deps, models, schemas
from ..config import get_settings
from ..constants import Roles
from ..utils.security import create_access_token, get_password_hash, verify_password
from ..utils.file_naming import FILENAME_MAX_LENGTH, FILENAME_SEPARATOR, slugify_filename

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
UPLOAD_DIR = Path(settings.upload_dir)
USER_UPLOAD_SUBDIR = "users"
MAX_CCCD_BYTES = 5 * 1024 * 1024
ALLOWED_CCCD_TYPES = {"image/png"}


@router.post("/register", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(
    email: EmailStr = Form(...),
    full_name: str = Form(..., min_length=2),
    password: str = Form(..., min_length=8),
    role: Roles = Form(Roles.PROVINCE_OFFICER),
    org_level: str = Form(...),
    org_name: str = Form(...),
    position: str | None = Form(None),
    cccd: str = Form(...),
    province: str | None = Form(None),
    district: str | None = Form(None),
    commune: str | None = Form(None),
    is_active: bool = Form(True),
    cccd_image: UploadFile = File(...),
    db: Session = Depends(deps.get_db),
) -> models.User:
    existing = db.query(models.User).filter(models.User.email == email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    if cccd_image.content_type not in ALLOWED_CCCD_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PNG files are allowed")

    target_dir = UPLOAD_DIR / USER_UPLOAD_SUBDIR
    target_dir.mkdir(parents=True, exist_ok=True)
    extension = Path(cccd_image.filename or "").suffix or ".png"
    safe_cccd = slugify_filename(cccd or "")
    safe_name = slugify_filename(full_name)
    prefix_parts = [part for part in ["cccd", safe_cccd, safe_name] if part]
    raw_name = f"{FILENAME_SEPARATOR.join(prefix_parts)}{extension}"
    stored_name = raw_name[:FILENAME_MAX_LENGTH]
    file_path = target_dir / stored_name
    counter = 1
    stem = Path(stored_name).stem
    while file_path.exists():
        candidate = f"{stem}{FILENAME_SEPARATOR}{counter}{extension}"
        stored_name = candidate[:FILENAME_MAX_LENGTH]
        file_path = target_dir / stored_name
        counter += 1

    total_bytes = 0
    try:
        async with aiofiles.open(file_path, "wb") as out_file:
            while True:
                chunk = await cccd_image.read(1024 * 1024)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_CCCD_BYTES:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File exceeds 5MB")
                await out_file.write(chunk)
    except HTTPException:
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        raise

    image_url = f"/files/{USER_UPLOAD_SUBDIR}/{quote(stored_name)}"
    user = models.User(
        email=email,
        full_name=full_name,
        hashed_password=get_password_hash(password),
        role=role,
        org_level=org_level,
        org_name=org_name,
        position=position,
        cccd=cccd,
        cccd_image_url=image_url,
        province=province,
        district=district,
        commune=commune,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.Token)
def login(
    credentials: schemas.UserLogin, db: Session = Depends(deps.get_db)
) -> schemas.Token:
    user = deps.authenticate_user(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    token = create_access_token(subject=user.email)
    return schemas.Token(access_token=token)


@router.get("/me", response_model=schemas.UserRead)
def read_current_user(current_user: models.User = Depends(deps.get_current_user)) -> models.User:
    return current_user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: schemas.ChangePasswordRequest,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> None:
    if not verify_password(payload.old_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Old password is incorrect")
    current_user.hashed_password = get_password_hash(payload.new_password)
    db.add(current_user)
    db.commit()
