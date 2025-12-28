"""AI服务提供商基类"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import httpx
import logging

logger = logging.getLogger(__name__)


class BaseAIProvider(ABC):
    """AI服务提供商基类"""

    def __init__(self, api_key: str, model: str, **kwargs):
        self.api_key = api_key
        self.model = model
        self.config = kwargs
        self.base_url = kwargs.get("base_url", self.get_default_base_url())
        self.timeout = kwargs.get("timeout", 60.0)

    @abstractmethod
    async def chat(self, messages: List[Dict], **kwargs) -> Dict:
        """发送聊天请求

        Args:
            messages: 消息列表，格式为 [{"role": "system/user", "content": "..."}]
            **kwargs: 额外参数（temperature, max_tokens等）

        Returns:
            API响应的JSON数据
        """
        pass

    @abstractmethod
    async def test_connection(self) -> Dict:
        """测试API连接

        Returns:
            {"success": bool, "message": str}
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """获取提供商名称"""
        pass

    @abstractmethod
    def get_provider_id(self) -> str:
        """获取提供商ID（用于数据库存储）"""
        pass

    @abstractmethod
    def get_default_base_url(self) -> str:
        """获取默认API endpoint"""
        pass

    @abstractmethod
    def get_available_models(self) -> List[Dict]:
        """获取可用模型列表

        Returns:
            [{"id": "model-name", "name": "显示名称", "description": "描述"}]
        """
        pass

    def format_system_prompt(self, prompt: str) -> Dict:
        """格式化系统提示"""
        return {
            "role": "system",
            "content": prompt
        }

    def format_user_message(self, content: str) -> Dict:
        """格式化用户消息"""
        return {
            "role": "user",
            "content": content
        }

    async def _make_request(
        self,
        endpoint: str,
        headers: Dict,
        payload: Dict
    ) -> Dict:
        """通用的HTTP请求方法

        Args:
            endpoint: API endpoint路径
            headers: HTTP headers
            payload: 请求体

        Returns:
            响应JSON

        Raises:
            httpx.HTTPError: HTTP请求失败
        """
        # 如果endpoint为空，直接使用base_url（不再拼接）
        if endpoint:
            url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        else:
            url = self.base_url

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error: {str(e)}")
            raise
