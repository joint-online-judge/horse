from functools import lru_cache

from pydantic import BaseSettings


class Settings(BaseSettings):

    """
    Define the settings (config) of the website.

    The selected value is determined as follows (in descending order of priority):
    1. The command line arguments, e.g., '--db-host' is mapped to 'db-host'
    2. Environment variables, e.g., '$DB_HOST' is mapped to 'db-host'
    3. Variables loaded from a dotenv (.env) file
    4. The default field values for the Settings model
    """

    app_name: str = "JOJ Horse"

    host: str = "127.0.0.1"
    port: int = 34765
    http_url_prefix: str = "http://%s:%d" % (host, port)
    ws_url_prefix: str = "ws://%s:%d" % (host, port)
    debug: bool = False

    session_ttl: int = 14 * 24 * 60 * 60  # 14 days, in seconds

    # postgresql config
    db_host: str = "localhost"
    db_port: int = 5432
    db_username: str = "postgres"
    db_password: str = "pass"
    db_name: str = "horse-production"

    # redis config
    redis_host: str = "localhost"
    redis_port: int = 6379

    # jwt config
    jwt_secret: str = "secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_seconds: int = 14 * 24 * 60 * 60  # 14 days, in seconds

    # oauth config
    oauth_jaccount: bool = False
    oauth_jaccount_id: str = ""
    oauth_jaccount_secret: str = ""

    # sentry config
    dsn: str = ""
    traces_sample_rate: float = 1

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
