import uvicorn
import asyncio

from joj.horse import app
from joj.horse.config import settings
from joj.horse.utils.cli import cli_command


@cli_command()
def main():
    # loop = asyncio.get_event_loop()
    # print(loop)
    uvicorn.run(
        "joj.horse:app",
        host=settings.host, port=settings.port,
        debug=settings.debug, reload=settings.debug
    )


if __name__ == "__main__":
    main()
