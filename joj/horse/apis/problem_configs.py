import io
from pathlib import Path as PathlibPath
from typing import Any, BinaryIO, Dict, Optional, cast

import orjson
from fastapi import Body, Depends, File, Path, Query, UploadFile
from fastapi.responses import StreamingResponse
from uvicorn.config import logger

from joj.elephant.schemas import ArchiveType, FileInfo
from joj.horse import models, schemas
from joj.horse.schemas import Empty, StandardResponse
from joj.horse.schemas.permission import Permission
from joj.horse.services.lakefs import LakeFSProblemConfig
from joj.horse.utils.base import TemporaryDirectory, iter_file
from joj.horse.utils.errors import BizError, ErrorCode
from joj.horse.utils.fastapi.router import MyRouter
from joj.horse.utils.lock import lock_problem_config
from joj.horse.utils.parser import (
    parse_file_path,
    parse_file_path_from_upload,
    parse_problem,
    parse_problem_config,
    parse_user_from_auth,
)

router = MyRouter()
router_name = "domains/{domain}/problems/{problem}"
router_tag = "problem config"
router_prefix = "/api/v1"


@router.put(
    "/config",
    description="Completely replace the problem config with the archive. "
    "This will delete files not included in the archive.",
    permissions=[Permission.DomainProblem.view_config, Permission.DomainProblem.edit],
    dependencies=[Depends(lock_problem_config)],
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
    # response_class=StreamingResponse,
    permissions=[Permission.DomainProblem.view_config],
)
def download_uncommitted_problem_config_as_archive(
    temp_dir: PathlibPath = Depends(TemporaryDirectory()),
    archive_format: ArchiveType = Query(ArchiveType.zip),
    problem: models.Problem = Depends(parse_problem),
) -> StandardResponse[Empty]:
    return download_problem_config_archive(temp_dir, archive_format, problem, None)


@router.get(
    "/config/files/{path:path}",
    # response_class=StreamingResponse,
    permissions=[Permission.DomainProblem.view_config],
)
def download_file_in_uncommitted_problem_config(
    path: str = Path(...),
    problem: models.Problem = Depends(parse_problem),
) -> Any:
    return download_file_in_problem_config(path, problem, None)


@router.get(
    "/config/file_info/{path:path}", permissions=[Permission.DomainProblem.view_config]
)
def get_file_or_directory_info_in_uncommitted_problem_config(
    path: str = Path(...),
    problem: models.Problem = Depends(parse_problem),
) -> StandardResponse[FileInfo]:
    problem_config = LakeFSProblemConfig(problem)
    file_info = problem_config.get_file_info(PathlibPath(path))
    return StandardResponse(file_info)


@router.put(
    "/config/files/{path:path}",
    description="Replace the file with the same path. "
    "Create directories if needed along the path.",
    permissions=[Permission.DomainProblem.view_config, Permission.DomainProblem.edit],
    dependencies=[Depends(lock_problem_config)],
)
def upload_file_to_problem_config(
    file: UploadFile = File(...),
    problem: models.Problem = Depends(parse_problem),
    path: str = Depends(parse_file_path),
) -> StandardResponse[FileInfo]:
    problem_config = LakeFSProblemConfig(problem)
    file_info = problem_config.upload_file(PathlibPath(path), cast(BinaryIO, file.file))
    return StandardResponse(file_info)


@router.put(
    "/config/files",
    description="Use the filename as path, "
    "file will be uploaded to root of the problem config directory.",
    permissions=[Permission.DomainProblem.view_config, Permission.DomainProblem.edit],
    dependencies=[Depends(lock_problem_config)],
)
def upload_file_to_root_in_problem_config(
    file: UploadFile = File(...),
    problem: models.Problem = Depends(parse_problem),
    path: str = Depends(parse_file_path_from_upload),
) -> StandardResponse[FileInfo]:
    return upload_file_to_problem_config(file, problem, path)


@router.delete(
    "/config/files/{path:path}",
    permissions=[Permission.DomainProblem.view_config, Permission.DomainProblem.edit],
    dependencies=[Depends(lock_problem_config)],
)
def delete_file_from_uncommitted_problem_config(
    path: str = Path(...),
    problem: models.Problem = Depends(parse_problem),
) -> StandardResponse[FileInfo]:
    problem_config = LakeFSProblemConfig(problem)
    file_info = problem_config.delete_file(PathlibPath(path))
    return StandardResponse(file_info)


@router.delete(
    "/config/dirs/{path:path}",
    permissions=[Permission.DomainProblem.view_config, Permission.DomainProblem.edit],
    dependencies=[Depends(lock_problem_config)],
)
def delete_directory_from_uncommitted_problem_config(
    path: str = Path(...),
    problem: models.Problem = Depends(parse_problem),
    recursive: bool = Query(
        False,
        description="Act as -r in the rm command. "
        "If false, only empty directory can be deleted.",
    ),
) -> StandardResponse[FileInfo]:
    problem_config = LakeFSProblemConfig(problem)
    file_info = problem_config.delete_directory(PathlibPath(path), recursive)
    return StandardResponse(file_info)


@router.post(
    "/config/commit",
    description="Commit all changes through upload / delete as a new problem config version.",
    permissions=[Permission.DomainProblem.view_config, Permission.DomainProblem.edit],
    dependencies=[Depends(lock_problem_config)],
)
async def commit_problem_config(
    commit: schemas.ProblemConfigCommit = Body(...),
    problem: models.Problem = Depends(parse_problem),
    user: models.User = Depends(parse_user_from_auth),
) -> StandardResponse[schemas.ProblemConfig]:
    result = await models.ProblemConfig.make_commit(
        problem=problem, committer=user, commit=commit
    )
    logger.info("problem config commit: %s", result)
    return StandardResponse(schemas.ProblemConfig.from_orm(result))


@router.post(
    "/config/reset",
    permissions=[Permission.DomainProblem.view_config, Permission.DomainProblem.edit],
    dependencies=[Depends(lock_problem_config)],
)
def reset_problem_config(
    lakefs_reset: schemas.LakeFSReset,
    problem: models.Problem = Depends(parse_problem),
) -> StandardResponse[Empty]:
    problem_config = LakeFSProblemConfig(problem)
    problem_config.reset(lakefs_reset)
    return StandardResponse()


@router.get("/configs/{config}", permissions=[Permission.DomainProblem.view_config])
async def get_problem_config_json(
    config: models.ProblemConfig = Depends(parse_problem_config),
    problem: models.Problem = Depends(parse_problem),
) -> StandardResponse[schemas.ProblemConfigDataDetail]:
    problem_config = LakeFSProblemConfig(problem)
    try:
        data = problem_config.get_config(config.commit_id)
    except BizError as e:
        if e.error_code != ErrorCode.FileValidationError:
            raise e
    # TODO: cache the archive
    # response = StreamingResponse(iter_file(file_path))
    res = schemas.ProblemConfigDataDetail.from_orm(config)
    res.data = data
    return StandardResponse(res)


@router.put(
    "/configs",
    permissions=[Permission.DomainProblem.view_config, Permission.DomainProblem.edit],
    dependencies=[Depends(lock_problem_config)],
)
def update_problem_config_json(
    config: Dict[str, Any] = Body(...),
    problem: models.Problem = Depends(parse_problem),
) -> StandardResponse[FileInfo]:
    problem_config = LakeFSProblemConfig(problem)
    file_info = problem_config.upload_file(
        PathlibPath("config.json"),
        io.BytesIO(orjson.dumps(config, option=orjson.OPT_INDENT_2)),
    )
    return StandardResponse(file_info)


@router.get(
    "/configs/{config}/files",
    permissions=[Permission.DomainProblem.view_config, Permission.DomainProblem.edit],
)
def download_problem_config_archive(
    temp_dir: PathlibPath = Depends(TemporaryDirectory()),
    archive_format: ArchiveType = Query(ArchiveType.zip),
    problem: models.Problem = Depends(parse_problem),
    config: Optional[models.ProblemConfig] = Depends(parse_problem_config),
) -> Any:
    # use lakefs to sync and zip files
    ref: Optional[str]
    if config is not None:
        ref = config.commit_id
    else:
        ref = None
    problem_config = LakeFSProblemConfig(problem)
    file_path = problem_config.download_archive(temp_dir, archive_format, ref)
    # TODO: cache the archive
    response = StreamingResponse(iter_file(file_path))
    # response.content_disposition = f'attachment; filename="{file_path.name}"'
    return response


@router.get(
    "/configs/{config}/files/{path:path}",
    # response_class=StreamingResponse,
    permissions=[Permission.DomainProblem.view_config],
)
def download_file_in_problem_config(
    path: str = Path(...),
    problem: models.Problem = Depends(parse_problem),
    config: Optional[models.ProblemConfig] = Depends(parse_problem_config),
) -> Any:
    problem_config = LakeFSProblemConfig(problem)
    ref: Optional[str]
    if config is not None:
        ref = config.commit_id
    else:
        ref = None
    file = problem_config.download_file(PathlibPath(path), ref)
    response = StreamingResponse(file)
    # filename = PathlibPath(path).name
    # response.content_disposition = f'attachment; filename="{filename}"'
    return response
