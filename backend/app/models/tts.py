from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, Boolean
from sqlalchemy.sql import func
from ..core.database import Base
import enum


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TTSRequest(Base):
    __tablename__ = "tts_requests"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    voice = Column(String(50), default="zh-CN-XiaoxiaoNeural")
    rate = Column(String(20), default="-15%")
    pitch = Column(String(20), default="-2Hz")
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    audio_url = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)
    task_id = Column(String(100), unique=True, index=True)
    total_chunks = Column(Integer, default=0)
    processed_chunks = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)