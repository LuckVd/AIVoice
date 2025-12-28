"""智谱AI GLM Provider"""
import logging
from typing import Dict, List
from .base_provider import BaseAIProvider

logger = logging.getLogger(__name__)


class GLMProvider(BaseAIProvider):
    """智谱AI GLM提供商

    文档: https://open.bigmodel.cn/dev/api
    """

    def get_default_base_url(self) -> str:
        return "https://open.bigmodel.cn/api/paas/v4/chat/completions"

    def get_provider_name(self) -> str:
        return "智谱AI (GLM)"

    def get_provider_id(self) -> str:
        return "glm"

    def get_available_models(self) -> List[Dict]:
        return [
            {
                "id": "glm-4-flash",
                "name": "GLM-4-Flash",
                "description": "免费，速度快，推荐使用"
            },
            {
                "id": "glm-4-plus",
                "name": "GLM-4-Plus",
                "description": "更强性能，收费"
            },
            {
                "id": "glm-4-air",
                "name": "GLM-4-Air",
                "description": "经济实惠"
            },
            {
                "id": "glm-4-0520",
                "name": "GLM-4-0520",
                "description": "最新版本"
            },
            {
                "id": "glm-3-turbo",
                "name": "GLM-3-Turbo",
                "description": "便宜，速度快"
            }
        ]

    async def chat(self, messages: List[Dict], **kwargs) -> Dict:
        """调用GLM API

        Args:
            messages: 消息列表
            **kwargs: 额外参数（temperature, max_tokens, top_p等）

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
            "temperature": kwargs.get("temperature", float(self.config.get("temperature", 0.7))),
            "max_tokens": kwargs.get("max_tokens", self.config.get("max_tokens", 4096)),
            "top_p": kwargs.get("top_p", 0.9),
            "stream": False
        }

        try:
            result = await self._make_request("", headers, payload)
            return result
        except Exception as e:
            logger.error(f"GLM API调用失败: {str(e)}")
            raise

    async def test_connection(self) -> Dict:
        """测试GLM API连接

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
