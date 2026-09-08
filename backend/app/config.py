from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings, read from backend/.env or the process environment."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    ENV: str = "development"

    # Which LLM answers /ask. Each provider uses its own key and model below.
    LLM_PROVIDER: Literal["groq", "anthropic"] = "groq"

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"

    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-5"

    # Runs locally in the MCP server; not tied to either provider.
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    MAX_TOKENS: int = 500
    RATE_LIMIT_PER_MINUTE: int = 10

    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:8081"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


settings = Settings()
