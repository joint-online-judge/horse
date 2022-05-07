from datetime import datetime, timezone

import pbr.version
from git.exc import GitCommandError, InvalidGitRepositoryError
from git.repo.base import Repo
from loguru import logger


def get_version() -> str:
    return str(pbr.version.VersionInfo("joj-horse"))


def get_git_version() -> str:
    try:
        repo = Repo(__file__, search_parent_directories=True)
        return (
            repo.git.describe(always=True, tags=True)
            + "@"
            + datetime.fromtimestamp(
                repo.head.commit.committed_date, tz=timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
        )
    except (InvalidGitRepositoryError, GitCommandError) as e:  # pragma: no cover
        logger.error(f"Failed to get repository: {repr(e)}")
        return "unknown"
