"""AI分析相关的数据模式"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime


class AIConfigCreate(BaseModel):
    """创建AI配置请求"""
    provider: str = Field(..., description="AI服务商 (glm/kimi/deepseek)")
    api_key: str = Field(..., description="API密钥")
    model: str = Field(..., description="模型名称")
    base_url: Optional[str] = Field(None, description="自定义API endpoint")
    temperature: str = "0.7"
    max_tokens: int = 4096


class AIConfigUpdate(BaseModel):
    """更新AI配置请求"""
    provider: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    temperature: Optional[str] = None
    max_tokens: Optional[int] = None


class AIConfigResponse(BaseModel):
    """AI配置响应"""
    id: int
    provider: str
    model: str
    is_active: bool
    is_default: bool
    created_at: datetime


class DialogSegment(BaseModel):
    """对话片段"""
    index: int
    type: str  # narration/dialog
    text: str
    speaker: Optional[str] = None
    emotion: Optional[str] = "neutral"
    context: Optional[str] = None
    text_segment_index: Optional[int] = None
    global_start_pos: Optional[int] = None


class CharacterInfo(BaseModel):
    """角色信息"""
    name: str
    dialog_count: int = 0
    first_appearance: int = 0


class AnalysisResult(BaseModel):
    """分析结果"""
    segments: List[DialogSegment]
    characters: Dict[str, CharacterInfo]
    text_segments: List[str]
    analysis_metadata: Dict[str, Any]


class AnalysisRequest(BaseModel):
    """分析请求"""
    text: str = Field(..., description="待分析的文本")
    ai_config_id: Optional[int] = Field(None, description="AI配置ID")
    enable_dialog_analysis: bool = True
    enable_character_extraction: bool = True


class AnalysisResponse(BaseModel):
    """分析响应"""
    analysis_id: str
    status: str  # processing/completed/failed
    progress: float = 0.0
    result: Optional[AnalysisResult] = None
    error: Optional[str] = None


class TestConnectionRequest(BaseModel):
    """测试连接请求"""
    provider: str
    api_key: str
    model: str
    base_url: Optional[str] = None
