from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..constants import CollectionStatus
from ..database import Base


class DataCollection(Base):
    __tablename__ = "data_collections"

    id = Column(Integer, primary_key=True, index=True)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)
    collector_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(Enum(CollectionStatus), default=CollectionStatus.DRAFT, nullable=False)
    notes = Column(Text, nullable=True)
    collected_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    household = relationship("Household", back_populates="data_collections")
    collector = relationship("User", back_populates="data_collections")
