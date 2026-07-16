from typing import Literal
from pydantic import AnyHttpUrl, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.config.defaults import DEFAULT_CONFIG


class DatabaseSettings(BaseSettings):
    engine: str = "memgraph"
    uri: str = "bolt://localhost:7687"
    user: str = ""
    password: str = ""

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
    api_key: SecretStr | None = None
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


def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings()


def get_tei_client_settings() -> TEIClientSettings:
    return TEIClientSettings()


def get_similarity_settings() -> ThemeSimilaritySettings:
    return ThemeSimilaritySettings()
