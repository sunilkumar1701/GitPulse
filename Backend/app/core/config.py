"""
Application configuration using Pydantic Settings.
Loads environment variables from .env file.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    PORT: int = 5000
    GITHUB_API: str = "https://api.github.com"
    GITHUB_TOKEN: str = ""
    GITHUB_MCP_PAT: str = ""
    
    # Groq AI — used by the new agentic chatbot
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"

    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_SECRET_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""

    # CORS
    CORS_ORIGINS: str = "*"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    Uses lru_cache so the .env file is read only once.
    """
    return Settings()
