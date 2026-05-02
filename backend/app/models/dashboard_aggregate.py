from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Index, Integer, String

from ..constants import PovertyStatus
from ..database import Base


class DashboardAggregate(Base):
    __tablename__ = "dashboard_aggregates"

    id = Column(Integer, primary_key=True, index=True)
    scope_type = Column(String(16), nullable=False)
    scope_name = Column(String(120), nullable=False)
    survey_year = Column(Integer, nullable=False)
    poverty_status = Column(Enum(PovertyStatus), nullable=False)
    household_count = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_dashboard_agg_scope_year_status", "scope_type", "scope_name", "survey_year", "poverty_status", unique=True),
        Index("ix_dashboard_agg_year", "survey_year"),
    )
