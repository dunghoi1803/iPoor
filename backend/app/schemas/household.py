from datetime import date, datetime

from pydantic import BaseModel, Field

from ..constants import PovertyStatus


class HouseholdBase(BaseModel):
    household_code: str = Field(min_length=3)
    head_name: str = Field(min_length=2)
    birth_date: date | None = None
    gender: str | None = None
    id_card: str | None = None
    address_line: str | None = None
    province: str
    district: str
    commune: str
    poverty_status: PovertyStatus
    ethnicity: str | None = None
    members_count: int | None = Field(default=None, ge=0)
    income_per_capita: float | None = Field(default=None, ge=0)
    score_b1: int | None = Field(default=None, ge=0)
    score_b2: int | None = Field(default=None, ge=0)
    note: str | None = None
    area: str | None = None
    village: str | None = None
    officer: str | None = None
    remark: str | None = None
    attachment_url: str | None = None
    last_surveyed_at: date | None = None


class HouseholdCreate(HouseholdBase):
    household_code: str | None = None


class HouseholdUpdate(BaseModel):
    household_code: str | None = None
    head_name: str | None = None
    birth_date: date | None = None
    gender: str | None = None
    id_card: str | None = None
    address_line: str | None = None
    province: str | None = None
    district: str | None = None
    commune: str | None = None
    poverty_status: PovertyStatus | None = None
    ethnicity: str | None = None
    members_count: int | None = Field(default=None, ge=0)
    income_per_capita: float | None = Field(default=None, ge=0)
    score_b1: int | None = Field(default=None, ge=0)
    score_b2: int | None = Field(default=None, ge=0)
    note: str | None = None
    area: str | None = None
    village: str | None = None
    officer: str | None = None
    remark: str | None = None
    attachment_url: str | None = None
    last_surveyed_at: date | None = None


class HouseholdRead(HouseholdBase):
    id: int
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class HouseholdListResponse(BaseModel):
    items: list[HouseholdRead]
    total: int
