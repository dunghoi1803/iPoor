from datetime import datetime

from pydantic import BaseModel

from ..constants import CollectionStatus


class DataCollectionBase(BaseModel):
    household_id: int
    collector_id: int | None = None
    status: CollectionStatus = CollectionStatus.DRAFT
    notes: str | None = None
    collected_at: datetime | None = None


class DataCollectionCreate(DataCollectionBase):
    pass


class DataCollectionUpdate(BaseModel):
    collector_id: int | None = None
    status: CollectionStatus | None = None
    notes: str | None = None
    collected_at: datetime | None = None


class DataCollectionRead(DataCollectionBase):
    id: int
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class DataCollectionUploadError(BaseModel):
    row: int
    column: str
    message: str


class DataCollectionUploadRow(BaseModel):
    row: int
    name: str | None = None
    id_card: str | None = None
    poverty_status: str | None = None
    birth_date: str | None = None
    gender: str | None = None
    ethnic: str | None = None
    address_line: str | None = None
    family_mem: int | None = None
    classified_before_check: str | None = None
    b1_score: int | None = None
    b2_score: int | None = None
    income_per_capita: float | None = None
    area: str | None = None
    description: str | None = None
    note: str | None = None
    pdf_url: str | None = None
    province: str | None = None
    district: str | None = None
    commune: str | None = None
    village: str | None = None
    date_check: str | None = None
    official_check: str | None = None
    valid: bool
    errors: list[DataCollectionUploadError] = []


class DataCollectionUploadResult(BaseModel):
    validRecords: int
    errorRecords: int
    errors: list[DataCollectionUploadError]
    rows: list[DataCollectionUploadRow] = []
