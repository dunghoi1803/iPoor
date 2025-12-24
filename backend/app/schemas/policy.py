from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from ..constants import POLICY_SUMMARY_MAX_LENGTH, PolicyCategory


class PolicyBase(BaseModel):
    title: str = Field(min_length=3)
    category: PolicyCategory
    summary: str | None = Field(default=None, max_length=POLICY_SUMMARY_MAX_LENGTH)
    description: str | None = None
    content_blocks: dict[str, Any] | None = None
    effective_date: date | None = None
    issued_by: str | None = None
    attachment_url: str | None = None
    tags: list[str] | None = None
    is_public: bool | None = None


class PolicyCreate(PolicyBase):
    pass


class PolicyUpdate(BaseModel):
    title: str | None = None
    category: PolicyCategory | None = None
    summary: str | None = Field(default=None, max_length=POLICY_SUMMARY_MAX_LENGTH)
    description: str | None = None
    content_blocks: dict[str, Any] | None = None
    effective_date: date | None = None
    issued_by: str | None = None
    attachment_url: str | None = None
    tags: list[str] | None = None
    is_public: bool | None = None


class PolicyRead(PolicyBase):
    id: int
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
