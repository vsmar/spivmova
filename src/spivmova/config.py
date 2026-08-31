from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    deepl_api_key: str
    youtube_api_key: str
    spacy_model: str = "uk_core_news_sm"
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()