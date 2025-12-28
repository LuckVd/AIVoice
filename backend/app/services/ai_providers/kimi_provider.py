"""Kimi (月之暗面) Provider"""
import logging
from typing import Dict, List
from .base_provider import BaseAIProvider

logger = logging.getLogger(__name__)


class KimiProvider(BaseAIProvider):
    """Kimi (月之暗面)提供商

    文档: https://platform.moonshot.cn/docs
    """

    def get_default_base_url(self) -> str:
        return "https://api.moonshot.cn/v1/chat/completions"

    def get_provider_name(self) -> str:
        return "Kimi (月之暗面)"

    def get_provider_id(self) -> str:
        return "kimi"

    def get_available_models(self) -> List[Dict]:
        return [
            {
                "id": "moonshot-v1-8k",
                "name": "Moonshot v1-8K",
                "description": "免费，8K上下文"
            },
            {
                "id": "moonshot-v1-32k",
                "name": "Moonshot v1-32K",
                "description": "收费，32K上下文"
            },
            {
                "id": "moonshot-v1-128k",
                "name": "Moonshot v1-128K",
                "description": "最强，128K超长上下文"
            }
        ]

    async def chat(self, messages: List[Dict], **kwargs) -> Dict:
        """调用Kimi API

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Returns:
            API响应
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", float(self.config.get("temperature", 0.3))),
            "max_tokens": kwargs.get("max_tokens", self.config.get("max_tokens", 4096)),
            "top_p": kwargs.get("top_p", 0.9),
            "stream": False
        }

        try:
            result = await self._make_request("", headers, payload)
            return result
        except Exception as e:
            logger.error(f"Kimi API调用失败: {str(e)}")
            raise

    async def test_connection(self) -> Dict:
        """测试Kimi API连接

        Returns:
            {"success": bool, "message": str}
        """
        try:
            messages = [
                self.format_system_prompt("你是一个助手。"),
                self.format_user_message("测试")
            ]

            result = await self.chat(messages)

            if "choices" in result and len(result["choices"]) > 0:
                return {
                    "success": True,
                    "message": f"连接成功！模型: {self.model}"
                }
            else:
                return {
                    "success": False,
                    "message": f"API返回异常: {result}"
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"连接失败: {str(e)}"
            }
