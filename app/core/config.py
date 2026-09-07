from functools import lru_cache

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and optional .env files."""

    ollama_base_url: HttpUrl = Field(default="http://localhost:11434/v1")
    default_model: str = Field(default="llama3.2")
    http_timeout: float = Field(default=15.0, gt=0)
    browser_timeout: int = Field(default=20_000, gt=0)
    min_content_length: int = Field(default=200, ge=1)
    max_context_chars: int = Field(default=12_000, ge=1_000)
    api_host: str = Field(default="127.0.0.1")
    api_port: int = Field(default=8000, ge=1, le=65_535)
    cors_origins: str = Field(default="http://localhost:7860,http://127.0.0.1:7860")
    api_base_url: HttpUrl = Field(default="http://127.0.0.1:8000")
    gradio_host: str = Field(default="127.0.0.1")
    gradio_port: int = Field(default=7860, ge=1, le=65_535)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
