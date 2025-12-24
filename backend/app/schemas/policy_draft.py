from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from ..constants import POLICY_SUMMARY_MAX_LENGTH, PolicyCategory


class PolicyDraftBase(BaseModel):
    policy_id: int | None = None
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


class PolicyDraftUpsert(PolicyDraftBase):
    pass


class PolicyDraftRead(PolicyDraftBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
