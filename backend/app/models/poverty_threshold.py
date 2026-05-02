from sqlalchemy import Column, Integer, String
from ..database import Base


class PovertyThreshold(Base):
    __tablename__ = "poverty_thresholds"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False, index=True)
    area_type = Column(String(50), nullable=False)  # 'Thành thị' or 'Nông thôn'
    b1_threshold = Column(Integer, nullable=False)  # Mức trần điểm B1 (Thu nhập)
    b2_deprived_min = Column(Integer, nullable=False, default=30)  # Mức tối thiểu điểm B2 (Thiếu hụt)
