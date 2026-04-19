from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Multi-Agent App Scaffolder")
    app_env: str = Field(default="dev")
    log_level: str = Field(default="INFO")

    gemini_api_key: str | None = Field(default=None)
    gemini_model: str = Field(default="gemini-2.5-flash-lite")
    gemini_model_planner: str | None = Field(default=None)
    gemini_model_architect: str | None = Field(default=None)
    gemini_model_schema: str | None = Field(default=None)
    gemini_model_api: str | None = Field(default=None)
    gemini_model_frontend: str | None = Field(default=None)
    gemini_model_reviewer: str | None = Field(default=None)
    gemini_max_retries: int = Field(default=3)
    gemini_retry_base_delay_seconds: float = Field(default=0.8)
    gemini_retry_max_delay_seconds: float = Field(default=6.0)
    smart_enable_stage_cache: bool = Field(default=True)
    smart_reviewer_on_clean: bool = Field(default=False)

    runs_dir: str = Field(default="runs")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def runs_path(self) -> Path:
        return Path(self.runs_dir)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
