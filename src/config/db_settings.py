from pydantic_settings import BaseSettings, SettingsConfigDict

class DatabaseSettings(BaseSettings):
    engine: str = "memgraph"
    uri: str = "bolt://localhost:7687"
    user: str = ""
    password: str = ""

    model_config = SettingsConfigDict(
        env_prefix="GRAPH_DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

def get_db_settings() -> DatabaseSettings:
    return DatabaseSettings()
