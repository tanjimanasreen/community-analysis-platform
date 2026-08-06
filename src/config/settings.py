from typing import Literal, Optional
from pydantic import AnyHttpUrl, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.config.defaults import DEFAULT_CONFIG


class DatabaseSettings(BaseSettings):
    engine: str = "memgraph"
    uri: str = "bolt://localhost:7687"
    user: Optional[str] = None
    password: Optional[str] = None
    database: str = "memgraph"

    model_config = SettingsConfigDict(
        env_prefix="GRAPH_DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )


class TEIClientSettings(BaseSettings):
    """Settings used by the application when calling TEI."""

    base_url: AnyHttpUrl = Field(default="http://127.0.0.1:8080")
    api_key: Optional[SecretStr] = None
    client_batch_size: int = Field(default=32, ge=1)
    timeout_seconds: float = Field(default=60.0, gt=0)

    model_config = SettingsConfigDict(
        env_prefix="TEI_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )


class ThemeSimilaritySettings(BaseSettings):
    provider: Literal["tei", "mock"] = "tei"
    failure_policy: Literal["fail", "mock"] = "fail"
    reply_transition_threshold: float = Field(
        default_factory=lambda: DEFAULT_CONFIG.similarity.reply_transition_threshold
    )
    default_transition_threshold: float = Field(
        default_factory=lambda: DEFAULT_CONFIG.similarity.default_transition_threshold
    )

    model_config = SettingsConfigDict(
        env_prefix="THEME_SIMILARITY_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )


class ProviderSettings(BaseSettings):
    """Settings for all LLM providers."""

    openai_api_key: Optional[SecretStr] = None
    openai_base_url: Optional[AnyHttpUrl] = None

    gemini_api_key: Optional[SecretStr] = None

    llm7_api_key: Optional[SecretStr] = None
    llm7_base_url: Optional[AnyHttpUrl] = None

    mistral_api_key: Optional[SecretStr] = None
    mistral_base_url: Optional[AnyHttpUrl] = None

    nvidia_api_key: Optional[SecretStr] = None
    nvidia_base_url: Optional[AnyHttpUrl] = None

    ollama_base_url: Optional[AnyHttpUrl] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )


class APISettings(BaseSettings):
    """Settings for the FastAPI application and Graph Builder."""

    artifact_root: Optional[str] = Field(
        default=None, alias="COMMUNITY_ANALYSIS_ARTIFACT_ROOT"
    )
    cors_origins: str = ""
    max_graph_nodes: int = 1000
    max_graph_edges: int = 5000
    catalog_refresh_seconds: float = 1.0
    parquet_cache_max_bytes: int = 16 * 1024 * 1024
    allowed_hosts: str = ""
    root_path: str = ""
    docs_enabled: bool = True
    gzip_minimum_size: int = Field(default=1024, ge=0)

    model_config = SettingsConfigDict(
        env_prefix="COMMUNITY_ANALYSIS_API_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )


class ProjectSettings(BaseSettings):
    """Settings used for interpolating YAML configurations."""

    data_root: str = "data"
    longitudinal_output: str = "results/longitudinal"
    longitudinal_theme_output: str = "results/themes/longitudinal"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )


def get_interpolated_env_vars() -> dict[str, str]:
    db = get_database_settings()
    proj = get_project_settings()

    return {
        "GRAPH_DB_URI": str(db.uri) if db.uri else "",
        "GRAPH_DB_USER": db.user or "",
        "GRAPH_DB_PASSWORD": db.password or "",
        "GRAPH_DB_DATABASE": db.database or "",
        "DATA_ROOT": proj.data_root,
        "LONGITUDINAL_OUTPUT": proj.longitudinal_output,
        "LONGITUDINAL_THEME_OUTPUT": proj.longitudinal_theme_output,
    }


def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings()


def get_tei_client_settings() -> TEIClientSettings:
    return TEIClientSettings()


def get_similarity_settings() -> ThemeSimilaritySettings:
    return ThemeSimilaritySettings()


def get_provider_settings() -> ProviderSettings:
    return ProviderSettings()


def get_api_settings() -> APISettings:
    return APISettings()


def get_project_settings() -> ProjectSettings:
    return ProjectSettings()
