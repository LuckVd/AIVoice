from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from ..core.database import Base


class SavedAudio(Base):
    """保存的音频模型"""
    __tablename__ = "saved_audios"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(500), nullable=False)  # 用户自定义的名称
    original_task_id = Column(String(100), nullable=False)  # 原始任务ID
    audio_path = Column(String(500), nullable=False)  # 音频文件路径
    text = Column(Text, nullable=True)  # 原始文本
    voice = Column(String(50), nullable=True)  # 使用的语音
    duration_seconds = Column(Integer, nullable=True)  # 音频时长（秒）
    file_size_bytes = Column(Integer, nullable=True)  # 文件大小
    created_at = Column(DateTime(timezone=True), server_default=func.now())
