from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    oracle_env: str = "development"
    database_url: str = "sqlite:///./oracle.db"
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5173"
    api_keys: str = Field(default="", validation_alias="ORACLE_API_KEYS")
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-flash"
    deepseek_timeout_seconds: float = 30.0
    ai_data_sharing_enabled: bool = False
    otel_service_name: str = "oracle-api"
    otel_exporter_otlp_traces_endpoint: str = Field(default="", validation_alias="OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
