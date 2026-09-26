from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "SENTI-MIND"
    environment: str = "development"
    database_url: str = f"sqlite:///{(PROJECT_ROOT / 'data' / 'senti_mind.db').as_posix()}"
    model_path: str = str(PROJECT_ROOT / "artifacts" / "baseline.joblib")
    max_text_length: int = 5000

    model_config = SettingsConfigDict(env_file=".env", env_prefix="SENTI_MIND_", extra="ignore")

    @property
    def resolved_model_path(self) -> Path:
        return Path(self.model_path).expanduser()


@lru_cache
def get_settings() -> Settings:
    return Settings()
