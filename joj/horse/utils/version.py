from datetime import datetime

import git
import pbr.version
from uvicorn.config import logger


def get_version() -> str:
    return str(pbr.version.VersionInfo("joj-horse"))


def get_git_version() -> str:
    try:
        return (
            git.Repo(__file__, search_parent_directories=True).git.describe(
                always=True, tags=True
            )
            + "@"
            + datetime.fromtimestamp(
                git.Repo(
                    __file__, search_parent_directories=True
                ).head.commit.committed_date
            ).strftime("%Y-%m-%d %H:%M:%S")
        )
    except (
        git.InvalidGitRepositoryError,
        git.GitCommandError,
    ) as e:  # pragma: no cover
        logger.error("Failed to get repository: %s", repr(e))
        return "unknown"
