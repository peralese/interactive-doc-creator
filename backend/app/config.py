"""Application configuration management."""

from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProviderConfig(BaseSettings):
    """Configuration for a single LLM provider."""
    
    api_key: str = ""
    model: str
    temperature: float = 0.7
    max_tokens: int = 2000


class Settings(BaseSettings):
    """Application settings loaded from environment variables and config files."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    app_name: str = "Interactive Document Creator"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    
    # Database
    database_url: str = "sqlite+aiosqlite:///../data/sessions.db"
    
    # Storage
    audio_storage_path: str = "../data/audio"
    session_storage_path: str = "../data/sessions"
    template_storage_path: str = "../templates"
    
    # LLM Configuration
    llm_default_provider: Literal["openai", "anthropic", "ollama"] = "openai"
    
    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4"
    openai_temperature: float = 0.7
    
    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-sonnet-20240229"
    anthropic_temperature: float = 0.7
    
    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:latest"
    ollama_temperature: float = 0.7
    
    # Speech-to-Text (Whisper)
    whisper_model: Literal["tiny", "base", "small", "medium", "large"] = "base"
    whisper_language: str = "en"
    whisper_device: Literal["cpu", "cuda"] = "cpu"
    whisper_compute_type: str = "int8"  # int8, float16, float32
    max_audio_size: int = 100_000_000  # 100MB
    max_requirements_size: int = 1_000_000  # 1MB of extracted text
    
    # Document Generation
    max_document_size: int = 1_000_000  # 1MB
    supported_export_formats: list[str] = Field(
        default_factory=lambda: ["markdown", "pdf", "docx", "html"]
    )
    
    # Session Management
    session_timeout_minutes: int = 60
    max_sessions_per_user: int = 10
    auto_save_interval_seconds: int = 30
    
    # Security
    secret_key: str = "change-this-in-production-use-openssl-rand-hex-32"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_environment(cls, value):
        """Tolerate common shell DEBUG modes that are not boolean values."""
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "production", "prod"}:
                return False
            if normalized in {"debug", "development", "dev"}:
                return True
        return value
    
    def get_llm_provider_config(
        self, provider: Literal["openai", "anthropic", "ollama"]
    ) -> dict:
        """Get configuration for a specific LLM provider."""
        if provider == "openai":
            return {
                "api_key": self.openai_api_key,
                "model": self.openai_model,
                "temperature": self.openai_temperature,
            }
        elif provider == "anthropic":
            return {
                "api_key": self.anthropic_api_key,
                "model": self.anthropic_model,
                "temperature": self.anthropic_temperature,
            }
        elif provider == "ollama":
            return {
                "base_url": self.ollama_base_url,
                "model": self.ollama_model,
                "temperature": self.ollama_temperature,
            }
        else:
            raise ValueError(f"Unknown provider: {provider}")


# Global settings instance
settings = Settings()

# Made with Bob
