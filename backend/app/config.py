from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/promptdb"

    app_port: int = 4165
    allowed_origin: str = "http://localhost:4163"

    translate_concurrency: int = 5
    request_timeout: float = 30.0


settings = Settings()