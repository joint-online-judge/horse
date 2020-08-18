import uvicorn

from joj.horse import app
from joj.horse.config import cli_command, cli_async, settings
from joj.horse.utils.session import get_caches


@cli_command()
def main():
    uvicorn.run(app, host=settings.host, port=settings.port)

if __name__ == "__main__":
    main()
