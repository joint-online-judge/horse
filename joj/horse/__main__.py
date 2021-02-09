import uvicorn

from joj.horse.config import settings
from joj.horse.utils.cli import cli_command


@cli_command()
def main():
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["default"]["fmt"] = "[%(levelname)1.1s %(asctime)s %(filename)s:%(lineno)d] %(message)s"
    log_config["formatters"]["default"]["datefmt"] = "%Y-%m-%d %H:%M:%S"
    uvicorn.run(
        "joj.horse:app",
        host=settings.host, port=settings.port,
        reload=settings.debug, log_config=log_config,
    )


if __name__ == "__main__":
    main()
