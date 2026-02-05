"""Configuration management for RheaRouter"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    app_name: str = "RheaRouter"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_timeout: int = 300

    # Rate Limiting
    global_rate_limit: int = 60  # requests per minute
    per_client_rate_limit: int = 20  # requests per minute
    rate_limit_burst: int = 10

    # VRAM Flow Valve
    vision_slots: int = 1
    text_slots: int = 2

    # Model Configuration
    default_text_model: str = "llama3.1:8b"
    default_vision_model: str = "minicpm-v:8b"
    reasoning_model: str = "deepseek-r1:8b"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


def get_settings() -> Settings:
    """Get application settings"""
    return Settings()
