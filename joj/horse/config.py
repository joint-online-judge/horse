from typing import Type, Union

from pydantic import Field
from pydantic_universal_settings import (
    BaseSettings,
    CLIWatchMixin,
    EnvFileMixin,
    add_settings,
    generate_all_settings,
    get_settings_proxy,
)


@add_settings
class ServerSettings(BaseSettings):
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
    workers: int = Field(1, description="Uvicorn workers count.")

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


@add_settings
class DatabaseSettings(BaseSettings):
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
    redis_password: str = ""
    redis_db_index: int = 0

    # rabbitmq config
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_username: str = "guest"
    rabbitmq_password: str = "guest"
    rabbitmq_vhost: str = ""


@add_settings
class ObjectStorageSettings(BaseSettings):
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
    lakefs_s3_domain: str = "s3.lakefs.example.com"
    lakefs_host: str = ""
    lakefs_port: int = 34766
    lakefs_username: str = "lakefs"
    lakefs_password: str = "lakefs"

    # buckets
    bucket_config: str = "s3://joj-config"
    bucket_submission: str = "s3://joj-submission"


@add_settings
class AuthSettings(BaseSettings):
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

    # rollbar config
    rollbar_access_token: str = ""


GeneratedSettings: Type[
    Union[
        ServerSettings,
        DatabaseSettings,
        ObjectStorageSettings,
        AuthSettings,
    ]
] = generate_all_settings(mixins=[EnvFileMixin, CLIWatchMixin])


class AllSettings(GeneratedSettings):  # type: ignore
    """
    Define the settings (config) of the website.

    The selected value is determined as follows (in descending order of priority):
    1. The command line arguments, e.g., '--db-host' is mapped to 'db_host'
    2. Environment variables, e.g., '$DB_HOST' is mapped to 'db_host'
    3. Variables loaded from a dotenv (.env) file, e.g., 'DB_HOST' is mapped to 'db_host'
    4. The default field values for the Settings model
    """


settings: AllSettings = get_settings_proxy()
