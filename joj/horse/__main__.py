import uvicorn

# from joj.horse import app
from joj.horse.config import cli_command, settings


@cli_command()
def main():
    uvicorn.run("joj.horse:app", host=settings.host, port=settings.port, debug=settings.debug, reload=settings.debug)


if __name__ == "__main__":
    main()
