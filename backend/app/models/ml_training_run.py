from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from ..database import Base


class MlTrainingRun(Base):
    __tablename__ = "ml_training_runs"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(64), nullable=False)
    model_version = Column(String(64), nullable=False, index=True)
    schedule_type = Column(String(24), nullable=False, default="manual")
    status = Column(String(24), nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    predicted_for_year = Column(Integer, nullable=True)
    pr_auc = Column(Float, nullable=True)
    train_rows = Column(Integer, nullable=True)
    prediction_rows = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
