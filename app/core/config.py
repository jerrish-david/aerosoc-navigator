from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AeroSOC Navigator"
    app_env: str = "development"
    app_debug: bool = True
    api_v1_prefix: str = "/api/v1"
    default_low_confidence_threshold: float = 0.70
    default_min_citation_count: int = 2

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "aerosoc"
    postgres_user: str = "aerosoc"
    postgres_password: str = "change_me"

    azure_openai_endpoint: str = ""
    azure_openai_deployment: str = ""
    azure_openai_api_version: str = ""

    jwt_issuer: str = ""
    jwt_audience: str = ""
    audit_chain_seed: str = "replace_me"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

