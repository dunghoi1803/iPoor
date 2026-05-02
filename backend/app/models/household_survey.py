from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..constants import PovertyStatus
from ..database import Base


class HouseholdSurvey(Base):
    __tablename__ = "household_surveys"

    id = Column(Integer, primary_key=True, index=True)
    household_id = Column(Integer, ForeignKey("households.id", ondelete="CASCADE"), nullable=False)
    survey_year = Column(Integer, nullable=False, index=True)
    survey_date = Column(Date, nullable=False)
    poverty_status = Column(Enum(PovertyStatus), nullable=False, index=True)
    members_count = Column(Integer, nullable=True)
    income_per_capita = Column(Float, nullable=True)
    score_b1 = Column(Integer, nullable=True)
    score_b2 = Column(Integer, nullable=True)
    note = Column(Text, nullable=True)
    officer = Column(String(255), nullable=True)
    remark = Column(Text, nullable=True)
    attachment_url = Column(String(1024), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    household = relationship("Household", back_populates="surveys")
