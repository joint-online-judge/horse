import git
import pbr.version
from uvicorn.config import logger


def get_version():
    return str(pbr.version.VersionInfo("joj.horse"))


def get_git_version():
    try:
        return git.Repo(__file__, search_parent_directories=True).git.describe(
            always=True, tags=True
        )
    except (git.InvalidGitRepositoryError, git.GitCommandError) as e:
        logger.error("Failed to get repository: %s", repr(e))
        return "unknown"
