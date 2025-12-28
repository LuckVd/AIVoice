"""AI Provider工厂"""
from typing import Dict, List, TYPE_CHECKING
import logging

from .base_provider import BaseAIProvider
from .glm_provider import GLMProvider
from .kimi_provider import KimiProvider
from .deepseek_provider import DeepSeekProvider

if TYPE_CHECKING:
    from ..models.ai_config import AIConfig

logger = logging.getLogger(__name__)


class AIProviderFactory:
    """AI Provider工厂类"""

    _providers = {
        "glm": GLMProvider,
        "kimi": KimiProvider,
        "deepseek": DeepSeekProvider,
    }

    @classmethod
    def create_provider(cls, ai_config: "AIConfig") -> BaseAIProvider:
        """根据配置创建Provider实例

        Args:
            ai_config: AIConfig模型实例

        Returns:
            BaseAIProvider实例

        Raises:
            ValueError: 不支持的provider
        """
        provider_class = cls._providers.get(ai_config.provider)

        if not provider_class:
            raise ValueError(
                f"不支持的AI服务商: {ai_config.provider}. "
                f"支持的服务商: {list(cls._providers.keys())}"
            )

        return provider_class(
            api_key=ai_config.api_key,
            model=ai_config.model,
            base_url=ai_config.base_url,
            temperature=float(ai_config.temperature),
            max_tokens=ai_config.max_tokens
        )

    @classmethod
    def create_provider_from_dict(cls, config: Dict) -> BaseAIProvider:
        """从字典配置创建Provider实例

        Args:
            config: 配置字典，包含provider, api_key, model等

        Returns:
            BaseAIProvider实例
        """
        provider_class = cls._providers.get(config.get("provider"))

        if not provider_class:
            raise ValueError(
                f"不支持的AI服务商: {config.get('provider')}. "
                f"支持的服务商: {list(cls._providers.keys())}"
            )

        return provider_class(
            api_key=config.get("api_key", ""),
            model=config.get("model", ""),
            base_url=config.get("base_url"),
            temperature=float(config.get("temperature", 0.7)),
            max_tokens=config.get("max_tokens", 4096)
        )

    @classmethod
    def get_available_providers(cls) -> List[Dict]:
        """获取所有可用的提供商信息

        Returns:
            [{"id": "glm", "name": "智谱AI", ...}, ...]
        """
        providers = []
        for provider_id, provider_class in cls._providers.items():
            # 创建临时实例以获取信息
            temp_instance = provider_class(api_key="temp", model="temp")
            providers.append({
                "id": provider_id,
                "name": temp_instance.get_provider_name(),
                "models": temp_instance.get_available_models()
            })

        return providers

    @classmethod
    def get_provider_info(cls, provider_id: str) -> Dict:
        """获取指定提供商的信息

        Args:
            provider_id: provider ID

        Returns:
            提供商信息字典
        """
        provider_class = cls._providers.get(provider_id)
        if not provider_class:
            raise ValueError(f"不支持的provider: {provider_id}")

        temp_instance = provider_class(api_key="temp", model="temp")
        return {
            "id": provider_id,
            "name": temp_instance.get_provider_name(),
            "models": temp_instance.get_available_models()
        }
