from datetime import datetime, timezone

import git
import pbr.version
from loguru import logger


def get_version() -> str:
    return str(pbr.version.VersionInfo("joj-horse"))


def get_git_version() -> str:
    try:
        repo = git.Repo(__file__, search_parent_directories=True)
        return (
            repo.git.describe(always=True, tags=True)
            + "@"
            + datetime.fromtimestamp(
                repo.head.commit.committed_date, tz=timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
        )
    except (
        git.InvalidGitRepositoryError,
        git.GitCommandError,
    ) as e:  # pragma: no cover
        logger.error("Failed to get repository: %s" % repr(e))
        return "unknown"
