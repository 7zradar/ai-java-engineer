"""Application configuration using Pydantic Settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application configuration loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General Environment
    env: str = Field(default="development", description="Runtime environment")
    log_level: str = Field(default="INFO", description="Logging level")
    app_host: str = Field(default="0.0.0.0", description="API host")
    app_port: int = Field(default=8000, description="API port")

    # Database / Persistence
    database_url: str = Field(
        default="sqlite+aiosqlite:///./ai_java_engineer.db",
        description="Database connection URL",
    )

    # LLM Settings
    default_llm_provider: str = Field(default="mock", description="mock | gemini | openai | anthropic")
    openai_api_key: str | None = Field(default=None)
    gemini_api_key: str | None = Field(default=None)
    anthropic_api_key: str | None = Field(default=None)

    # Execution Backend Settings (Python host -> Remote Java CI)
    execution_backend: str = Field(default="mock", description="mock | remote_ci")
    remote_ci_endpoint: str | None = Field(default=None)
    remote_ci_auth_token: str | None = Field(default=None)
    remote_ci_timeout_seconds: int = Field(default=600)

    # Execution Budget Defaults
    max_total_tokens: int = Field(default=250_000)
    max_model_calls: int = Field(default=40)
    max_debug_iterations: int = Field(default=3)
    max_runtime_seconds: int = Field(default=1800)


_settings: AppSettings | None = None


def get_settings() -> AppSettings:
    """Singleton getter for application settings."""
    global _settings
    if _settings is None:
        _settings = AppSettings()
    return _settings
