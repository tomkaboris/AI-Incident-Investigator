import json
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class AIProvider(StrEnum):
    OPENAI = "openai"
    LITELLM = "litellm"


class StorageBackend(StrEnum):
    LOCAL = "local"
    S3 = "s3"


class Settings(BaseSettings):
    ai_provider: AIProvider = AIProvider.OPENAI
    ai_model: str = "gpt-5.4-mini"
    ai_api_key: str | None = None

    # Backward-compatible aliases for existing installations.
    openai_api_key: str | None = None
    openai_model: str | None = None

    session_secret_key: str = "change-this-development-secret"
    session_cookie_name: str = "incident_investigator_session"
    session_max_age_seconds: int = 60 * 60 * 24 * 7
    session_https_only: bool = False
    registration_enabled: bool = True
    max_log_characters: int = Field(default=50_000, ge=1_000, le=5_000_000)
    max_upload_size_bytes: int = Field(default=10 * 1024 * 1024, ge=1_024)
    max_problem_description_characters: int = Field(default=5_000, ge=100, le=50_000)
    allowed_log_extensions: str = ".log,.txt,.out,.err,.json,.jsonl,.csv,.yaml,.yml"
    allowed_log_content_types: str = (
        "text/plain,text/csv,application/json,application/x-ndjson,"
        "application/yaml,text/yaml,application/octet-stream"
    )
    reject_binary_logs: bool = True

    # Prices are USD per one million tokens. Keep this catalog current for your providers.
    ai_model_pricing_json: str = "{}"

    # Recursive archive ingestion limits.
    max_archive_upload_size_bytes: int = Field(default=500 * 1024 * 1024, ge=1024)
    max_archive_extracted_size_bytes: int = Field(default=2 * 1024 * 1024 * 1024, ge=1024)
    max_archive_file_count: int = Field(default=20_000, ge=1, le=1_000_000)
    max_archive_depth: int = Field(default=5, ge=0, le=20)
    max_single_extracted_file_size_bytes: int = Field(default=200 * 1024 * 1024, ge=1024)
    max_compression_ratio: float = Field(default=200.0, ge=1.0, le=100_000.0)
    archive_time_window_minutes: int = Field(default=15, ge=1, le=1440)
    max_archive_ai_characters: int = Field(default=250_000, ge=10_000, le=2_000_000)
    max_artifact_excerpt_characters: int = Field(default=8_000, ge=500, le=100_000)
    redact_secrets_before_ai: bool = True
    allow_raw_artifact_download: bool = False

    storage_backend: StorageBackend = StorageBackend.LOCAL
    local_storage_path: str = "./data/logs"
    s3_bucket: str | None = None
    s3_prefix: str = "incident-logs"
    s3_endpoint_url: str | None = None
    s3_region: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_use_ssl: bool = True

    database_url: str = "sqlite+aiosqlite:///./incident_investigator.db"
    database_echo: bool = False
    database_auto_create: bool = True

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def apply_legacy_openai_settings(self) -> "Settings":
        if self.openai_model:
            self.ai_model = self.openai_model
        if not self.ai_api_key and self.openai_api_key:
            self.ai_api_key = self.openai_api_key
        if self.storage_backend is StorageBackend.S3 and not self.s3_bucket:
            raise ValueError("S3_BUCKET is required when STORAGE_BACKEND=s3.")
        return self

    @property
    def allowed_log_extension_set(self) -> set[str]:
        return {
            item.strip().lower() for item in self.allowed_log_extensions.split(",") if item.strip()
        }

    @property
    def allowed_log_content_type_set(self) -> set[str]:
        return {
            item.strip().lower()
            for item in self.allowed_log_content_types.split(",")
            if item.strip()
        }

    def get_model_pricing(self, provider_name: str, model_name: str) -> dict[str, float] | None:
        try:
            catalog = json.loads(self.ai_model_pricing_json or "{}")
        except json.JSONDecodeError as exc:
            raise ValueError("AI_MODEL_PRICING_JSON must contain valid JSON.") from exc
        for key in (f"{provider_name}:{model_name}", model_name):
            value = catalog.get(key)
            if not isinstance(value, dict):
                continue
            if "input_per_1m" in value and "output_per_1m" in value:
                return {
                    "input_per_1m": float(value["input_per_1m"]),
                    "output_per_1m": float(value["output_per_1m"]),
                }
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()
