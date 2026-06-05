from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

PROJECT_ROOT = Path(__file__).parents[3]
ENV_FILE = PROJECT_ROOT / ".env"
CONFIG_FILE = PROJECT_ROOT / "config.yaml"


class Settings(BaseSettings):
    llm_provider: str
    llm_base_url: str
    llm_model: str
    llm_api_key: SecretStr
    rerank_base_url: str
    rerank_model: str
    embed_base_url: str
    embed_model: str
    postgres_url: SecretStr
    postgres_url_sync: SecretStr | None = None
    qdrant_url: str
    qdrant_collection: str = "rag_chunks"
    storage_backend: str = "rustfs"
    storage_endpoint: str
    storage_access_key: SecretStr
    storage_secret_key: SecretStr
    storage_bucket: str
    storage_region: str = "us-east-1"
    storage_public_endpoint: str | None = None
    app_env: Literal["dev", "development", "staging", "production"] = "dev"
    allow_local_idp_in_prod: bool = False
    idp_provider: Literal["local", "feishu", "wecom", "wechat_open", "wechat_mp"] = "local"
    local_users: str = "[]"
    app_port: int = 8000
    app_log_level: str = "INFO"

    chunk_size: int = 800
    chunk_overlap: int = 100
    top_k: int = 30
    rerank_n: int = 5
    min_score: float = 0.5
    temperature: float = 0.3
    max_tokens: int = 2000
    llm_timeout: int = 60
    llm_max_retries: int = 2
    router_confidence_threshold: float = 0.7
    ingest_concurrency: int = 5

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        yaml_settings = YamlConfigSettingsSource(
            settings_cls,
            yaml_file=CONFIG_FILE,
            yaml_file_encoding="utf-8",
        )
        return init_settings, env_settings, dotenv_settings, yaml_settings, file_secret_settings


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
