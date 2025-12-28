"""AI配置模型"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from ..core.database import Base


class AIConfig(Base):
    """AI API配置"""
    __tablename__ = "ai_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=True, index=True)  # 用户标识（可选，用于多用户）

    # API配置
    provider = Column(String(50), nullable=False)  # glm, kimi, deepseek
    api_key = Column(Text, nullable=False)  # API密钥（加密存储）
    model = Column(String(100), nullable=False)  # 模型名称

    # 可选配置
    base_url = Column(String(500))  # 自定义API endpoint
    temperature = Column(String(10), default="0.7")  # 温度参数
    max_tokens = Column(Integer, default=4096)  # 最大tokens

    # 状态
    is_active = Column(Boolean, default=True)  # 是否启用
    is_default = Column(Boolean, default=False)  # 是否默认配置
    last_tested = Column(DateTime)  # 最后测试时间
    test_status = Column(String(20))  # success/failed/pending
    test_message = Column(Text)  # 测试结果消息

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<AIConfig(provider={self.provider}, model={self.model})>"
