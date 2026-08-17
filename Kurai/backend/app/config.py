from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Environment
    ENV: str = "development"

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 10

    # LLM settings
    MAX_TOKENS: int = 500

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,https://kurai-frontend.vercel.app"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS string into list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


settings = Settings()
