from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from ..constants import POLICY_SUMMARY_MAX_LENGTH, PolicyCategory


class AttachmentFile(BaseModel):
    url: str
    name: str


class PolicyBase(BaseModel):
    title: str = Field(min_length=3)
    category: PolicyCategory
    summary: str | None = Field(default=None, max_length=POLICY_SUMMARY_MAX_LENGTH)
    description: str | None = None
    content_blocks: dict[str, Any] | list[dict[str, Any]] | None = None
    effective_date: date | None = None
    issued_by: str | None = None
    attachment_files: list[AttachmentFile] | None = None
    flipbook_url: str | None = None
    tags: list[str] | None = None
    is_public: bool | None = None


class PolicyCreate(PolicyBase):
    pass


class PolicyUpdate(BaseModel):
    title: str | None = None
    category: PolicyCategory | None = None
    summary: str | None = Field(default=None, max_length=POLICY_SUMMARY_MAX_LENGTH)
    description: str | None = None
    content_blocks: dict[str, Any] | list[dict[str, Any]] | None = None
    effective_date: date | None = None
    issued_by: str | None = None
    attachment_files: list[AttachmentFile] | None = None
    flipbook_url: str | None = None
    tags: list[str] | None = None
    is_public: bool | None = None


class PolicyRead(PolicyBase):
    id: int
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class PolicyBrief(BaseModel):
    id: int
    title: str | None = None
    summary: str | None = None
    description: str | None = None
    category: PolicyCategory | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
