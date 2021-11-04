from functools import lru_cache
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import (
    BaseModel,
    BaseSettings as PydanticBaseSettings,
    Field,
    root_validator,
)


class ServerSettings(BaseModel):
    """
    Server configuration

    The configuration of server connection, debug mode and proxy
    """

    app_name: str = Field("JOJ Horse", description="App name displayed in docs.")
    debug: bool = Field(True, description="Enable debug mode and hot reload.")
    https: bool = Field(
        None, description="Enable https. If not set, use 'not debug' as default."
    )

    host: str = Field("127.0.0.1", description="Bind socket to this host.")
    port: int = Field(34765, description="Bind socket to this port.")

    """
    Examples of  domain and root_path
    1. the server is deployed on https://www.example.com/
       set domain = "www.example.com" and root_path = ""
    2. the server is deployed on https://www.example.com:34765/joj/
       set domain = "www.example.com:34765" and root_path = "/joj"
    3. the server is deployed on http://127.0.0.1:34765/
       set domain = "127.0.0.1:34765" and root_path = ""
       or set domain = "" and root_path = "" if host = 127.0.0.1
    """
    domain: str = Field("", description="The domain of the server (for proxy usage)")
    root_path: str = Field("", description="ASGI root path (for proxy usage)")
    forwarded_allow_ips: str = Field(
        "127.0.0.1",
        description="Comma separated list of IPs to trust with proxy headers. "
        "A wildcard '*' means always trust.",
    )


class DatabaseSettings(BaseModel):
    """
    Database configuration

    The configuration of PostgreSQL and Redis
    """

    # postgresql config
    db_host: str = Field("localhost", description="Hostname of PostgreSQL server.")
    db_port: int = Field(5432, description="Port of PostgreSQL server.")
    db_username: str = "postgres"
    db_password: str = "pass"
    db_name: str = "horse_production"
    db_echo: bool = True

    # redis config
    redis_host: str = "localhost"
    redis_port: int = 6379


class ObjectStorageSettings(BaseModel):
    """
    Object storage configuration

    The configuration of Amazon S3 (or any S3 compatible service such as Minio) and LakeFS
    """

    # s3 config (any s3 compatible service)
    s3_host: str = ""
    s3_port: int = 80
    s3_username: str = ""
    s3_password: str = ""

    # lakefs config
    lakefs_host: str = ""
    lakefs_port: int = 34766
    lakefs_username: str = "lakefs"
    lakefs_password: str = "lakefs"

    # buckets
    bucket_config: str = "s3://joj-config"
    bucket_submission: str = "s3://joj-submission"


class AuthSettings(BaseModel):
    """
    Auth configuration

    The configuration of JWT, OAuth and Sentry
    """

    # jwt config
    jwt_secret: str = "secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_seconds: int = 14 * 24 * 60 * 60  # 14 days, in seconds

    # oauth config
    oauth_jaccount: bool = False
    oauth_jaccount_id: str = ""
    oauth_jaccount_secret: str = ""

    oauth_github: bool = False
    oauth_github_id: str = ""
    oauth_github_secret: str = ""

    # sentry config
    dsn: str = ""
    traces_sample_rate: float = 1


AllSettings: List[Type[BaseModel]] = [
    ServerSettings,
    DatabaseSettings,
    ObjectStorageSettings,
    AuthSettings,
]


class AllSettingsValidator(*AllSettings):  # type: ignore
    pass


class Settings(
    ServerSettings,
    DatabaseSettings,
    ObjectStorageSettings,
    AuthSettings,
    PydanticBaseSettings,
):
    """
    Define the settings (config) of the website.

    The selected value is determined as follows (in descending order of priority):
    1. The command line arguments, e.g., '--db-host' is mapped to 'db_host'
    2. Environment variables, e.g., '$DB_HOST' is mapped to 'db_host'
    3. Variables loaded from a dotenv (.env) file, e.g., 'DB_HOST' is mapped to 'db_host'
    4. The default field values for the Settings model
    """

    @classmethod
    def __inject_cli(cls, values: Dict[str, Any]) -> None:  # pragma: no cover
        from joj.horse.utils.cli import cli_settings

        AllSettingsValidator(**cli_settings)
        for key, value in cli_settings.items():
            if key in values and value is not None:
                values[key] = value

    @classmethod
    def __set_default_values(cls, values: Dict[str, Any]) -> None:
        if "domain" not in values or not values["domain"]:
            if "host" not in values or "port" not in values:
                raise ValueError()  # pragma: no cover
            if values["port"] == 80 or values["port"] == 443:
                values["domain"] = values["host"]  # pragma: no cover
            else:
                values["domain"] = "{}:{}".format(values["host"], values["port"])
        if "https" not in values or values["https"] is None:
            if "debug" not in values:
                raise ValueError()  # pragma: no cover
            values["https"] = not values["debug"]

    @root_validator()
    def finalize(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        cls.__inject_cli(values)
        cls.__set_default_values(values)
        return values

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class SettingsProxy:
    def __init__(self) -> None:
        self._settings: Optional[Settings] = None

    def _set(self, _settings: Settings) -> None:
        self._settings = _settings

    def __getattr__(self, attr: str) -> Any:
        if self._settings is None:
            raise ValueError("settings not initialized")  # pragma: no cover
        return getattr(self._settings, attr)


@lru_cache()
def get_settings() -> Settings:
    _settings = Settings()
    settings._set(_settings)  # type: ignore
    return _settings


settings: Union[Settings, SettingsProxy] = SettingsProxy()
