from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    frontend_origins: str = "https://egorfateew-ops.github.io,http://localhost:5500,http://127.0.0.1:5500"

    tecdoc_vin_base_url: str = "https://vehicle-identification.tecalliance.services"
    tecdoc_vin_api_key: str = ""
    tecdoc_vin_auth_header: str = "Authorization"
    tecdoc_vin_auth_prefix: str = ""
    tecdoc_vin_country: str = "RU"

    tecdoc_parts_url: str = ""
    tecdoc_parts_api_key: str = ""
    tecdoc_parts_auth_header: str = "Authorization"
    tecdoc_parts_auth_prefix: str = ""
    tecdoc_parts_method: str = "POST"
    tecdoc_parts_request_template: str = ""
    tecdoc_product_group_map: str = "{}"

    tecdoc_catalog_country: str = "RU"
    tecdoc_catalog_language: str = "RU"

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.frontend_origins.split(",") if item.strip()]

    @property
    def product_group_map(self) -> dict:
        import json
        try:
            value = json.loads(self.tecdoc_product_group_map or "{}")
            return value if isinstance(value, dict) else {}
        except json.JSONDecodeError:
            return {}


@lru_cache
def get_settings() -> Settings:
    return Settings()
