from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, Date, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import relationship

from ..constants import POLICY_SUMMARY_MAX_LENGTH, PolicyCategory
from ..database import Base


class Policy(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    category = Column(Enum(PolicyCategory), nullable=False)
    summary = Column(String(POLICY_SUMMARY_MAX_LENGTH), nullable=True)
    description = Column(Text, nullable=True)
    content_blocks = Column(JSON, nullable=True)
    effective_date = Column(Date, nullable=True)
    issued_by = Column(String(255), nullable=True)
    attachment_url = Column(String(255), nullable=True)
    tags = Column(JSON, nullable=True)
    is_public = Column(Boolean, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
