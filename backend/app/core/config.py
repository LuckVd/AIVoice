from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # App settings
    app_name: str = "AI Voice TTS API"
    debug: bool = False
    version: str = "0.1.0"

    # Database
    database_url: str = "postgresql://tts_user:tts_password@localhost:15432/tts_db"

    # Redis
    redis_url: str = "redis://localhost:16379"

    # Storage
    storage_path: str = "/opt/projects/AIVoice/storage"
    max_file_size: int = 10 * 1024 * 1024  # 10MB

    # TTS Settings
    voice: str = "zh-CN-XiaoxiaoNeural"
    rate: str = "-15%"
    pitch: str = "-20Hz"
    max_chars_per_chunk: int = 500
    max_retries: int = 3
    concurrency: int = 3

    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    class Config:
        env_file = ".env"


settings = Settings()