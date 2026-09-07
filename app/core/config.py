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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
