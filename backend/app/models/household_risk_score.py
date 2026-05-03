from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Index, Integer, String

from ..database import Base


class HouseholdRiskScore(Base):
    __tablename__ = "household_risk_scores"

    id = Column(Integer, primary_key=True, index=True)
    household_id = Column(Integer, nullable=False, index=True)
    survey_year = Column(Integer, nullable=False)
    predicted_for_year = Column(Integer, nullable=False, index=True)
    scope_region = Column(String(120), nullable=True, index=True)
    scope_province = Column(String(120), nullable=True, index=True)
    risk_score = Column(Float, nullable=False)
    risk_band = Column(String(24), nullable=False, index=True)
    model_name = Column(String(64), nullable=False, default="xgboost")
    model_version = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_risk_household_target_year", "household_id", "predicted_for_year", unique=True),
    )
