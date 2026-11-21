from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BACKEND_DIR / ".env"), extra="ignore")

    database_url: str = "sqlite:///./data/notes.db"  # set DATABASE_URL in .env to use PostgreSQL
    data_dir: str = str(BACKEND_DIR / "data")
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    request_delay_seconds: float = 1.0
    respect_robots_txt: bool = True
    user_agent: str = "LectureNotesCollector/1.0 (non-commercial educational research)"
    max_download_mb: int = 60

    ai_provider: str = "none"  # none | anthropic | openai
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5-5"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    @property
    def data_path(self) -> Path:
        p = Path(self.data_dir)
        if not p.is_absolute():
            p = BACKEND_DIR / p
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def ai_enabled(self) -> bool:
        if self.ai_provider == "anthropic":
            return bool(self.anthropic_api_key)
        if self.ai_provider == "openai":
            return bool(self.openai_api_key) or "localhost" in self.openai_base_url
        return False


@lru_cache
def get_settings() -> Settings:
    return Settings()
