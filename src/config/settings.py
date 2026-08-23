from typing import Literal, Optional
from pydantic import AliasChoices, AnyHttpUrl, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.config.defaults import DEFAULT_CONFIG

DEFAULT_SIMILARITY_MODEL_ID = "sentence-transformers/paraphrase-MiniLM-L6-v2"
DEFAULT_SIMILARITY_MODEL_REVISION = "c9a2bfebc254878aee8c3aca9e6844d5bbb102d1"
DEFAULT_CLUSTERING_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_CLUSTERING_MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"


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
    """Settings for the similarity TEI profile with legacy ``TEI_*`` aliases."""

    base_url: AnyHttpUrl = Field(
        default="http://127.0.0.1:8080",
        validation_alias=AliasChoices("TEI_SIMILARITY_BASE_URL", "TEI_BASE_URL"),
    )
    api_key: Optional[SecretStr] = Field(
        default=None,
        validation_alias=AliasChoices("TEI_SIMILARITY_API_KEY", "TEI_API_KEY"),
    )
    client_batch_size: int = Field(
        default=32,
        ge=1,
        validation_alias=AliasChoices(
            "TEI_SIMILARITY_CLIENT_BATCH_SIZE", "TEI_CLIENT_BATCH_SIZE"
        ),
    )
    timeout_seconds: float = Field(
        default=60.0,
        gt=0,
        validation_alias=AliasChoices(
            "TEI_SIMILARITY_TIMEOUT_SECONDS", "TEI_TIMEOUT_SECONDS"
        ),
    )
    model_id: str = Field(
        default=DEFAULT_SIMILARITY_MODEL_ID,
        validation_alias=AliasChoices("TEI_SIMILARITY_MODEL_ID", "TEI_MODEL_ID"),
    )
    revision: str = Field(
        default=DEFAULT_SIMILARITY_MODEL_REVISION,
        validation_alias=AliasChoices("TEI_SIMILARITY_REVISION", "TEI_REVISION"),
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
        populate_by_name=True,
    )


class TEIClusteringClientSettings(BaseSettings):
    """Settings used by the theme-clustering TEI profile."""

    base_url: AnyHttpUrl = Field(default="http://127.0.0.1:8081")
    api_key: Optional[SecretStr] = None
    client_batch_size: int = Field(default=32, ge=1)
    timeout_seconds: float = Field(default=60.0, gt=0)
    model_id: str = DEFAULT_CLUSTERING_MODEL_ID
    revision: str = DEFAULT_CLUSTERING_MODEL_REVISION

    model_config = SettingsConfigDict(
        env_prefix="TEI_CLUSTERING_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )


class ThemeClusteringSettings(BaseSettings):
    provider: Literal["tei", "mock"] = "tei"

    model_config = SettingsConfigDict(
        env_prefix="THEME_CLUSTERING_",
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


class AzureTranslatorSettings(BaseSettings):
    """Environment-only Azure Translator connection settings."""

    key: Optional[SecretStr] = None
    endpoint: AnyHttpUrl = Field(
        default="https://api.cognitive.microsofttranslator.com"
    )
    region: Optional[str] = None

    model_config = SettingsConfigDict(
        env_prefix="AZURE_TRANSLATOR_",
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
    }


def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings()


def get_tei_client_settings() -> TEIClientSettings:
    """Return similarity-profile settings; explicit aliases beat legacy ``TEI_*``."""
    return TEIClientSettings()


def get_clustering_tei_client_settings() -> TEIClusteringClientSettings:
    return TEIClusteringClientSettings()


def get_clustering_settings() -> ThemeClusteringSettings:
    return ThemeClusteringSettings()


def get_similarity_settings() -> ThemeSimilaritySettings:
    return ThemeSimilaritySettings()


def get_azure_translator_settings() -> AzureTranslatorSettings:
    return AzureTranslatorSettings()


def get_provider_settings() -> ProviderSettings:
    return ProviderSettings()


def get_api_settings() -> APISettings:
    return APISettings()


def get_project_settings() -> ProjectSettings:
    return ProjectSettings()
