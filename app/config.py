from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="Interview Analyzer", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    host: str = Field(default="127.0.0.1", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    llm_base_url: str = Field(default="http://127.0.0.1:8001/v1", alias="LLM_BASE_URL")
    llm_api_key: str = Field(default="local-dev-key", alias="LLM_API_KEY")
    llm_model: str = Field(default="Qwen/Qwen3-235B-A22B-Instruct-2507", alias="LLM_MODEL")
    llm_timeout_seconds: int = Field(default=120, alias="LLM_TIMEOUT_SECONDS")

    whisper_model: str = Field(default="large-v3", alias="WHISPER_MODEL")
    whisper_device: str = Field(default="cpu", alias="WHISPER_DEVICE")
    whisper_compute_type: str = Field(default="int8", alias="WHISPER_COMPUTE_TYPE")

    embedding_model: str = Field(default="BAAI/bge-m3", alias="EMBEDDING_MODEL")
    reranker_model: str = Field(default="BAAI/bge-reranker-v2-m3", alias="RERANKER_MODEL")

    max_questions: int = Field(default=3, alias="MAX_QUESTIONS")
    reports_dir: Path = Field(default=Path("storage/reports"), alias="REPORTS_DIR")
    uploads_dir: Path = Field(default=Path("storage/uploads"), alias="UPLOADS_DIR")
    sessions_dir: Path = Field(default=Path("storage/sessions"), alias="SESSIONS_DIR")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.sessions_dir.mkdir(parents=True, exist_ok=True)
    return settings
