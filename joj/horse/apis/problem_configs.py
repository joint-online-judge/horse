from pathlib import Path
from typing import Any, Optional

from fastapi import Body, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse
from joj.elephant.schemas import ArchiveType, FileInfo
from uvicorn.config import logger

from joj.horse import models, schemas

# from joj.horse.apis import records
from joj.horse.schemas import Empty, StandardResponse
from joj.horse.schemas.permission import Permission
from joj.horse.utils.auth import ensure_permission
from joj.horse.utils.base import TemporaryDirectory, iter_file
from joj.horse.utils.lakefs import LakeFSProblemConfig
from joj.horse.utils.parser import (
    parse_file_path,
    parse_file_path_from_upload,
    parse_problem,
    parse_problem_config,
    parse_user_from_auth,
)
from joj.horse.utils.router import MyRouter

router = MyRouter()
router_name = "domains/{domain}/problems/{problem}"
router_tag = "problem config"
router_prefix = "/api/v1"

read_dependency = Depends(ensure_permission(Permission.DomainProblem.view_config))
write_dependency = Depends(
    ensure_permission(
        [
            Permission.DomainProblem.view_config,
            Permission.DomainProblem.edit,
        ]
    )
)


@router.put(
    "/config",
    description="Completely replace the problem config with the archive. "
    "This will delete files not included in the archive.",
    dependencies=[write_dependency],
)
def update_problem_config_by_archive(
    file: UploadFile = File(...), problem: models.Problem = Depends(parse_problem)
) -> StandardResponse[Empty]:
    logger.info("problem config archive name: %s", file.filename)
    problem_config = LakeFSProblemConfig(problem)
    problem_config.upload_archive(file.filename, file.file)
    return StandardResponse()


@router.get(
    "/config",
    response_class=StreamingResponse,
    dependencies=[read_dependency],
)
def download_uncommitted_problem_config_as_archive(
    temp_dir: Path = Depends(TemporaryDirectory()),
    archive_type: ArchiveType = Query(ArchiveType.zip),
    problem: models.Problem = Depends(parse_problem),
) -> Any:
    return download_problem_config_archive(temp_dir, archive_type, problem, None)


@router.get(
    "/config/files/{path:path}",
    response_class=StreamingResponse,
    dependencies=[read_dependency],
)
def download_file_in_uncommitted_problem_config(
    path: str,
    problem: models.Problem = Depends(parse_problem),
) -> Any:
    return download_file_in_problem_config(path, problem, None)


@router.get(
    "/config/file_info/{path:path}",
    dependencies=[read_dependency],
)
def get_file_or_directory_info_in_uncommitted_problem_config(
    path: str,
    problem: models.Problem = Depends(parse_problem),
) -> StandardResponse[FileInfo]:
    problem_config = LakeFSProblemConfig(problem)
    file_info = problem_config.get_file_info(Path(path))
    return StandardResponse(file_info)


@router.put(
    "/config/files/{path:path}",
    description="Replace the file with the same path. "
    "Create directories if needed along the path.",
    dependencies=[write_dependency],
)
def upload_file_to_problem_config(
    file: UploadFile = File(...),
    problem: models.Problem = Depends(parse_problem),
    path: str = Depends(parse_file_path),
) -> StandardResponse[FileInfo]:
    problem_config = LakeFSProblemConfig(problem)
    file_info = problem_config.upload_file(Path(path), file.file)
    return StandardResponse(file_info)


@router.put(
    "/config/files",
    description="Use the filename as path, "
    "file will be uploaded to root of the problem config directory.",
    dependencies=[write_dependency],
)
def upload_file_to_root_in_problem_config(
    file: UploadFile = File(...),
    problem: models.Problem = Depends(parse_problem),
    path: str = Depends(parse_file_path_from_upload),
) -> StandardResponse[FileInfo]:
    return upload_file_to_problem_config(file, problem, path)


@router.delete(
    "/config/files/{path:path}",
    dependencies=[write_dependency],
)
def delete_file_from_uncommitted_problem_config(
    path: str,
    problem: models.Problem = Depends(parse_problem),
) -> StandardResponse[FileInfo]:
    problem_config = LakeFSProblemConfig(problem)
    file_info = problem_config.delete_file(Path(path))
    return StandardResponse(file_info)


@router.delete(
    "/config/dirs/{path:path}",
    dependencies=[write_dependency],
)
def delete_directory_from_uncommitted_problem_config(
    path: str,
    problem: models.Problem = Depends(parse_problem),
    recursive: bool = Query(
        False,
        description="Act as -r in the rm command. "
        "If false, only empty directory can be deleted.",
    ),
) -> StandardResponse[FileInfo]:
    problem_config = LakeFSProblemConfig(problem)
    file_info = problem_config.delete_directory(Path(path), recursive)
    return StandardResponse(file_info)


@router.post(
    "/config/commit",
    description="Commit all changes through upload / delete as a new problem config version.",
    dependencies=[write_dependency],
)
async def commit_problem_config(
    commit: schemas.ProblemConfigCommit = Body(...),
    problem: models.Problem = Depends(parse_problem),
    user: models.User = Depends(parse_user_from_auth),
) -> StandardResponse[schemas.ProblemConfig]:
    result = await models.ProblemConfig.make_commit(
        problem=problem, commiter=user, message=commit.message
    )
    logger.info("problem config commit: %s", result)
    return StandardResponse(schemas.ProblemConfig.from_orm(result))


@router.post(
    "/config/reset",
    dependencies=[write_dependency],
)
def reset_problem_config(
    lakefs_reset: schemas.LakeFSReset,
    problem: models.Problem = Depends(parse_problem),
) -> StandardResponse[Empty]:
    problem_config = LakeFSProblemConfig(problem)
    problem_config.reset(lakefs_reset)
    return StandardResponse()


@router.get(
    "/configs/{config}",
    dependencies=[read_dependency],
)
async def get_problem_config_json(
    config: models.ProblemConfig = Depends(parse_problem_config),
) -> StandardResponse[schemas.ProblemConfig]:
    return StandardResponse(schemas.ProblemConfig.from_orm(config))


@router.get(
    "/configs/{config}/files",
    dependencies=[write_dependency],
)
def download_problem_config_archive(
    temp_dir: Path = Depends(TemporaryDirectory()),
    archive_type: ArchiveType = Query(ArchiveType.zip),
    problem: models.Problem = Depends(parse_problem),
    config: Optional[models.ProblemConfig] = Depends(parse_problem_config),
) -> Any:
    # use lakefs to sync and zip files
    if config is not None:
        ref = config.commit_id
    else:
        ref = None
    problem_config = LakeFSProblemConfig(problem)
    file_path = problem_config.download_archive(temp_dir, archive_type, ref)
    # TODO: cache the archive
    response = StreamingResponse(iter_file(file_path))
    response.content_disposition = f'attachment; filename="{file_path.name}"'
    return response


@router.get(
    "/configs/{config}/files/{path:path}",
    response_class=StreamingResponse,
    dependencies=[read_dependency],
)
def download_file_in_problem_config(
    path: str,
    problem: models.Problem = Depends(parse_problem),
    config: Optional[models.ProblemConfig] = Depends(parse_problem_config),
) -> Any:
    problem_config = LakeFSProblemConfig(problem)
    if config is not None:
        ref = config.commit_id
    else:
        ref = None
    file = problem_config.download_file(Path(path), ref)
    response = StreamingResponse(file)
    filename = Path(path).name
    response.content_disposition = f'attachment; filename="{filename}"'
    return response
