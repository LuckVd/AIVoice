from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from ..models.tts import TaskStatus


class TTSRequestCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)
    voice: Optional[str] = Field("zh-CN-XiaoxiaoNeural", description="Voice model")
    rate: Optional[str] = Field("-15%", description="Speech rate")
    pitch: Optional[str] = Field("-2Hz", description="Voice pitch")


class TTSRequestResponse(BaseModel):
    id: int
    text: str
    voice: str
    rate: str
    pitch: str
    status: TaskStatus
    audio_url: Optional[str] = None
    error_message: Optional[str] = None
    task_id: str
    total_chunks: int
    processed_chunks: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    file_size_bytes: Optional[int] = None

    class Config:
        from_attributes = True


class TTSRequestUpdate(BaseModel):
    status: Optional[TaskStatus] = None
    audio_url: Optional[str] = None
    error_message: Optional[str] = None
    processed_chunks: Optional[int] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    file_size_bytes: Optional[int] = None


class TaskStatusResponse(BaseModel):
    task_id: str
    status: TaskStatus
    progress: float = Field(..., ge=0, le=1, description="Progress from 0 to 1")
    message: Optional[str] = None
    result_url: Optional[str] = None