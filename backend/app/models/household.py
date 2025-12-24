from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Enum, Float, Integer, String, Text
from sqlalchemy.orm import relationship

from ..constants import PovertyStatus
from ..database import Base


class Household(Base):
    __tablename__ = "households"

    id = Column(Integer, primary_key=True, index=True)
    household_code = Column(String(64), unique=True, index=True, nullable=False)
    head_name = Column(String(255), nullable=False)
    birth_date = Column(Date, nullable=True)
    gender = Column(String(16), nullable=True)
    id_card = Column(String(20), nullable=True)
    address_line = Column(Text, nullable=True)
    province = Column(String(120), nullable=False)
    district = Column(String(120), nullable=False)
    commune = Column(String(120), nullable=False)
    poverty_status = Column(Enum(PovertyStatus), nullable=False)
    ethnicity = Column(String(120), nullable=True)
    members_count = Column(Integer, nullable=True)
    income_per_capita = Column(Float, nullable=True)
    score_b1 = Column(Integer, nullable=True)
    score_b2 = Column(Integer, nullable=True)
    note = Column(Text, nullable=True)
    area = Column(String(120), nullable=True)
    village = Column(String(255), nullable=True)
    officer = Column(String(255), nullable=True)
    remark = Column(Text, nullable=True)
    attachment_url = Column(String(255), nullable=True)
    last_surveyed_at = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    activity_logs = relationship("ActivityLog", back_populates="household")
    data_collections = relationship("DataCollection", back_populates="household")
