from datetime import date, datetime

from pydantic import BaseModel, Field

from .household_survey import HouseholdSurveyRead, HouseholdSurveyCreate


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
    ethnicity: str | None = None
    area: str | None = None
    village: str | None = None


class HouseholdCreate(HouseholdBase):
    household_code: str | None = None
    survey: HouseholdSurveyCreate | None = None


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
    ethnicity: str | None = None
    area: str | None = None
    village: str | None = None
    survey: HouseholdSurveyCreate | None = None


class HouseholdRead(HouseholdBase):
    id: int
    created_at: datetime
    updated_at: datetime | None = None
    surveys: list[HouseholdSurveyRead] = []

    class Config:
        from_attributes = True


class HouseholdListResponse(BaseModel):
    items: list[HouseholdRead]
    total: int
