from datetime import datetime

from pydantic import BaseModel


class ActivityLogBase(BaseModel):
    action: str
    entity_type: str | None = None
    entity_id: int | None = None
    detail: str | None = None
    household_id: int | None = None
    ip_address: str | None = None


class ActivityLogCreate(ActivityLogBase):
    user_id: int | None = None


class ActivityLogRead(ActivityLogBase):
    id: int
    user_id: int | None = None
    created_at: datetime
    user_email: str | None = None
    user_role: str | None = None

    class Config:
        from_attributes = True
