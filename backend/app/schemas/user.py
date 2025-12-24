from pydantic import BaseModel, EmailStr, Field

from ..constants import Roles


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2)
    role: Roles = Roles.PROVINCE_OFFICER
    org_level: str | None = None
    org_name: str | None = None
    position: str | None = None
    cccd: str | None = None
    cccd_image_url: str | None = None
    province: str | None = None
    district: str | None = None
    commune: str | None = None
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: Roles | None = None
    org_level: str | None = None
    org_name: str | None = None
    position: str | None = None
    cccd: str | None = None
    cccd_image_url: str | None = None
    province: str | None = None
    district: str | None = None
    commune: str | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8)


class UserRead(UserBase):
    id: int

    class Config:
        from_attributes = True
