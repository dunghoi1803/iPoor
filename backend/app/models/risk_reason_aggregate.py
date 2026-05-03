from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Index, Integer, String

from ..database import Base


class RiskReasonAggregate(Base):
    __tablename__ = "risk_reason_aggregates"

    id = Column(Integer, primary_key=True, index=True)
    scope_type = Column(String(16), nullable=False, index=True)
    scope_name = Column(String(120), nullable=False, index=True)
    predicted_for_year = Column(Integer, nullable=False, index=True)
    reason_key = Column(String(64), nullable=False)
    reason_label = Column(String(255), nullable=False)
    importance = Column(Float, nullable=False)
    affected_households = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index(
            "ix_reason_scope_year_key",
            "scope_type",
            "scope_name",
            "predicted_for_year",
            "reason_key",
            unique=True,
        ),
    )
