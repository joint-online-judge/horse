import uvicorn

from joj.horse.config import get_settings
from joj.horse.utils.cli import cli_command
from joj.horse.utils.logger import log_config


@cli_command()
def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "joj.horse.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_config=log_config,
        reload_dirs=["joj"],
    )


if __name__ == "__main__":
    main()
