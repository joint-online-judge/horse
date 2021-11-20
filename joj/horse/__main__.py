from typing import List, Optional

import uvicorn

from joj.horse.config import get_settings
from joj.horse.utils.cli import cli_command


@cli_command()
def main() -> None:  # pragma: no cover
    settings = get_settings()
    reload_dirs: Optional[List[str]] = None
    if settings.debug:
        reload_dirs = ["joj", ".venv/lib/python3.8/site-packages/joj"]
    uvicorn.run(
        "joj.horse.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        forwarded_allow_ips=settings.forwarded_allow_ips,
        reload_dirs=reload_dirs,
        workers=settings.workers,
    )


if __name__ == "__main__":
    main()
