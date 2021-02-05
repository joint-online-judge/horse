import uvicorn

from joj.horse.config import settings
from joj.horse.utils.cli import cli_command


@cli_command()
def main():
    uvicorn.run(
        "joj.horse:app",
        host=settings.host, port=settings.port,
        reload=settings.debug
    )


if __name__ == "__main__":
    main()
