from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    env: str = "development"
    database_url: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
