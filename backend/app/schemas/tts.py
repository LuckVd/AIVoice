from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from ..models.tts import TaskStatus


class TTSRequestCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=200000, description="要转换的文本（支持长文本）")
    voice: Optional[str] = Field("zh-CN-XiaoxiaoNeural", description="Voice model")
    rate: Optional[str] = Field("-15%", description="Speech rate")
    pitch: Optional[str] = Field("-2Hz", description="Voice pitch")


class TTSRequestCreateSSML(BaseModel):
    """使用 SSML 的高级 TTS 请求"""
    text: str = Field(..., min_length=1, max_length=200000, description="要转换的文本（支持长文本）")
    ssml_preset: Optional[str] = Field(None, description="SSML 预设配置: BEDTIME_SOFT/BEDTIME_BALANCED/BEDTIME_FAIRY")
    use_ssml: Optional[bool] = Field(True, description="是否使用 SSML 生成")
    custom_ssml: Optional[bool] = Field(False, description="text是否为预先生成的完整SSML（多角色语音等）")

    # 高级配置（可选，覆盖预设）
    voice: Optional[str] = Field(None, description="语音模型，覆盖预设")
    style: Optional[str] = Field(None, description="语音风格，覆盖预设")
    role: Optional[str] = Field(None, description="角色扮演，覆盖预设")
    rate: Optional[str] = Field(None, description="语速，覆盖预设")
    pitch: Optional[str] = Field(None, description="音调，覆盖预设")
    comma_pause: Optional[str] = Field(None, description="逗号停顿，覆盖预设")
    sentence_pause: Optional[str] = Field(None, description="句子停顿，覆盖预设")

    # 保持向后兼容的传统参数
    legacy_mode: Optional[bool] = Field(False, description="使用传统模式（不使用 SSML）")
    legacy_rate: Optional[str] = Field("-15%", description="传统模式语速")
    legacy_pitch: Optional[str] = Field("-2Hz", description="传统模式音调")


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


class SSMLPresetResponse(BaseModel):
    """SSML 预设配置响应"""
    name: str
    description: str
    voice: str
    style: Optional[str]
    role: Optional[str]
    rate: str
    pitch: str
    comma_pause: str
    sentence_pause: str


class SSMLPresetsListResponse(BaseModel):
    """SSML 预设配置列表响应"""
    presets: Dict[str, SSMLPresetResponse]


class TTSRequestCreateSSMLResponse(BaseModel):
    """SSML TTS 请求创建响应"""
    task_id: str
    status: TaskStatus
    message: str
    ssml_used: bool
    ssml_preset: Optional[str] = None
    estimated_chunks: int = Field(..., description="预估的文本块数量")


class SSMLPreviewResponse(BaseModel):
    """SSML 预览响应"""
    ssml: str = Field(..., description="生成的 SSML")
    preset_used: Optional[str] = Field(None, description="使用的预设配置")
    estimated_duration: int = Field(..., description="预估音频时长（秒）")
    character_count: int = Field(..., description="文本字符数")