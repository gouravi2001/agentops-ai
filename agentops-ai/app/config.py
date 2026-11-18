from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./agentops.db"
    openai_api_key: str | None = None
    model_name: str = "gpt-4o-mini"
    model_timeout_seconds: float = Field(default=15.0, ge=1, le=30)
    max_tool_calls: int = Field(default=3, ge=1, le=5)
    enable_otel: bool = False

@lru_cache
def get_settings() -> Settings:
    return Settings()
