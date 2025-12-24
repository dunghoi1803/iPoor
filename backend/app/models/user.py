from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String
from sqlalchemy.orm import relationship

from ..constants import Roles
from ..database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(Roles), default=Roles.PROVINCE_OFFICER, nullable=False)
    org_level = Column(String(50), nullable=True)
    org_name = Column(String(255), nullable=True)
    position = Column(String(255), nullable=True)
    cccd = Column(String(32), nullable=True, index=True)
    cccd_image_url = Column(String(255), nullable=True)
    province = Column(String(120), nullable=True)
    district = Column(String(120), nullable=True)
    commune = Column(String(120), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    activity_logs = relationship("ActivityLog", back_populates="user")
    data_collections = relationship("DataCollection", back_populates="collector")
