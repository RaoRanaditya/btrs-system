from functools import lru_cache

class Settings:
    DATABASE_URL: str = "sqlite:///./bugtracker.db"
    DB_ECHO: bool = False

@lru_cache
def get_settings() -> Settings:
    return Settings()
