"""DeepSeek Provider"""
import logging
from typing import Dict, List
from .base_provider import BaseAIProvider

logger = logging.getLogger(__name__)


class DeepSeekProvider(BaseAIProvider):
    """DeepSeek提供商

    文档: https://platform.deepseek.com/api-docs/
    """

    def get_default_base_url(self) -> str:
        return "https://api.deepseek.com/chat/completions"

    def get_provider_name(self) -> str:
        return "DeepSeek"

    def get_provider_id(self) -> str:
        return "deepseek"

    def get_available_models(self) -> List[Dict]:
        return [
            {
                "id": "deepseek-chat",
                "name": "DeepSeek-Chat",
                "description": "主力模型，性价比高"
            },
            {
                "id": "deepseek-coder",
                "name": "DeepSeek-Coder",
                "description": "代码优化版本"
            }
        ]

    async def chat(self, messages: List[Dict], **kwargs) -> Dict:
        """调用DeepSeek API

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Returns:
            API响应
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", float(self.config.get("temperature", 0.7))),
            "max_tokens": kwargs.get("max_tokens", self.config.get("max_tokens", 4096)),
            "top_p": kwargs.get("top_p", 0.9),
            "stream": False
        }

        try:
            result = await self._make_request("", headers, payload)
            return result
        except Exception as e:
            logger.error(f"DeepSeek API调用失败: {str(e)}")
            raise

    async def test_connection(self) -> Dict:
        """测试DeepSeek API连接

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
