from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
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
    crm_provider: Literal["mock", "xiaoshouyi", "fxiaoke", "hubspot", "salesforce"] = "mock"
    mock_crm_data_path: str = "data/mock_crm"
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
    customer_master_excel_path: str = "data/customer_master_init_sample.xlsx"
    customer_match_fuzzy_threshold: int = Field(default=80, ge=0, le=100)
    customer_match_limit: int = Field(default=5, gt=0)
    extract_confidence_threshold: int = Field(default=70, ge=0, le=100)
    prompts_dir: str = "prompts"
    vision_dpi: int = Field(default=150, gt=0)
    vision_max_pages: int = Field(default=20, gt=0)

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
