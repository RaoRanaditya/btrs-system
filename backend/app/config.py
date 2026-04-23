from functools import lru_cache

class Settings:
    # SIMPLE FAST FIX (no external dependency)
    DATABASE_URL = "sqlite:///./test.db"

    DB_POOL_SIZE = 5
    DB_MAX_OVERFLOW = 10
    DB_POOL_TIMEOUT = 30
    DB_POOL_RECYCLE = 1800
    DB_ECHO = True


@lru_cache
def get_settings():
    return Settings()