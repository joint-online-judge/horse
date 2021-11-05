import uvicorn

from joj.horse.config import get_settings
from joj.horse.utils.cli import cli_command


@cli_command()
def main() -> None:  # pragma: no cover
    settings = get_settings()
    uvicorn.run(
        "joj.horse.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        forwarded_allow_ips=settings.forwarded_allow_ips,
        reload_dirs=["joj"],
    )


if __name__ == "__main__":
    main()
