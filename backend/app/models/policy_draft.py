from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, Date, DateTime, Enum, ForeignKey, Integer, String, Text

from ..constants import POLICY_SUMMARY_MAX_LENGTH, PolicyCategory
from ..database import Base


class PolicyDraft(Base):
    __tablename__ = "policy_drafts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    policy_id = Column(Integer, ForeignKey("policies.id"), nullable=True, index=True)
    title = Column(String(255), nullable=True)
    category = Column(
        Enum(PolicyCategory, values_callable=lambda value: [entry.value for entry in value]),
        nullable=True,
    )
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
