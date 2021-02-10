import uvicorn

from joj.horse.config import settings
from joj.horse.utils.cli import cli_command
from joj.horse.utils.logger import log_config


@cli_command()
def main():
    uvicorn.run(
        "joj.horse:app",
        host=settings.host, port=settings.port,
        reload=settings.debug, log_config=log_config,
    )


if __name__ == "__main__":
    main()
