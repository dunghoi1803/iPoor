from datetime import date, datetime

from pydantic import BaseModel, Field

from ..constants import PovertyStatus


class HouseholdSurveyBase(BaseModel):
    survey_year: int
    survey_date: date
    poverty_status: PovertyStatus
    members_count: int | None = Field(default=None, ge=0)
    income_per_capita: float | None = Field(default=None, ge=0)
    score_b1: int | None = Field(default=None, ge=0)
    score_b2: int | None = Field(default=None, ge=0)
    note: str | None = None
    officer: str | None = None
    remark: str | None = None
    attachment_url: str | None = None


class HouseholdSurveyCreate(HouseholdSurveyBase):
    survey_year: int | None = None  # auto-derived from survey_date if not provided
    survey_date: date | None = None  # allow None so FE can omit
    poverty_status: PovertyStatus | None = None


class HouseholdSurveyUpdate(BaseModel):
    survey_year: int | None = None
    survey_date: date | None = None
    poverty_status: PovertyStatus | None = None
    members_count: int | None = Field(default=None, ge=0)
    income_per_capita: float | None = Field(default=None, ge=0)
    score_b1: int | None = Field(default=None, ge=0)
    score_b2: int | None = Field(default=None, ge=0)
    note: str | None = None
    officer: str | None = None
    remark: str | None = None
    attachment_url: str | None = None


class HouseholdSurveyRead(HouseholdSurveyBase):
    id: int
    household_id: int
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
