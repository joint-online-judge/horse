import io
from pathlib import Path as PathlibPath
from typing import Any, Optional

import orjson
from fastapi import Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool
from uvicorn.config import logger

from joj.elephant.schemas import ArchiveType
from joj.horse import models, schemas
from joj.horse.schemas import StandardResponse
from joj.horse.schemas.base import StandardListResponse
from joj.horse.schemas.permission import Permission
from joj.horse.services.lakefs import LakeFSProblemConfig
from joj.horse.utils.base import TemporaryDirectory, iter_file
from joj.horse.utils.errors import BizError, ErrorCode
from joj.horse.utils.fastapi.router import MyRouter
from joj.horse.utils.lock import lock_problem_config
from joj.horse.utils.parser import (
    parse_ordering_query,
    parse_pagination_query,
    parse_problem,
    parse_problem_config,
    parse_user_from_auth,
)

router = MyRouter()
router_name = "domains/{domain}/problems/{problem}"
router_tag = "problem config"


@router.get(
    "/configs",
    permissions=[Permission.DomainProblem.view_config],
)
async def list_problem_config_commits(
    problem: models.Problem = Depends(parse_problem),
    ordering: schemas.OrderingQuery = Depends(parse_ordering_query()),
    pagination: schemas.PaginationQuery = Depends(parse_pagination_query),
) -> StandardListResponse[schemas.ProblemConfigDetail]:
    statement = problem.find_problem_config_commits_statement()
    commits, count = await models.ProblemConfig.execute_list_statement(
        statement, ordering, pagination
    )
    return StandardListResponse(commits, count)


@router.post(
    "/configs",
    description="Completely replace the problem config with the archive. "
    "This will delete files not included in the archive.",
    permissions=[Permission.DomainProblem.view_config, Permission.DomainProblem.edit],
    dependencies=[Depends(lock_problem_config)],
)
async def update_problem_config_by_archive(
    file: UploadFile = File(...),
    config_json_on_missing: schemas.ConfigJsonOnMissing = schemas.ConfigJsonOnMissing.raise_error,
    problem: models.Problem = Depends(parse_problem),
    user: models.User = Depends(parse_user_from_auth),
) -> StandardResponse[schemas.ProblemConfigDetail]:
    logger.info("problem config archive name: %s", file.filename)

    def sync_func() -> None:
        problem_config = LakeFSProblemConfig(problem)
        problem_config.upload_problem_config_archive(
            file.filename, file.file, config_json_on_missing
        )

    await run_in_threadpool(sync_func)
    result = await models.ProblemConfig.make_commit(
        problem=problem,
        committer=user,
        commit=schemas.ProblemConfigCommit(message="", data_version=2),
    )
    logger.info("problem config commit: %s", result)
    return StandardResponse(schemas.ProblemConfigDetail.from_orm(result))


@router.post(
    "/configs/json",
    permissions=[Permission.DomainProblem.view_config, Permission.DomainProblem.edit],
    dependencies=[Depends(lock_problem_config)],
)
async def update_problem_config_json(
    config: schemas.ProblemConfigJson,
    problem: models.Problem = Depends(parse_problem),
    user: models.User = Depends(parse_user_from_auth),
) -> StandardResponse[schemas.ProblemConfigDetail]:
    def sync_func() -> None:
        problem_config = LakeFSProblemConfig(problem)
        problem_config.upload_file(
            PathlibPath("config.json"),
            io.BytesIO(orjson.dumps(config.dict(), option=orjson.OPT_INDENT_2)),
        )

    await run_in_threadpool(sync_func)
    result = await models.ProblemConfig.make_commit(
        problem=problem,
        committer=user,
        commit=schemas.ProblemConfigCommit(message="", data_version=2),
    )
    logger.info("problem config commit: %s", result)
    return StandardResponse(schemas.ProblemConfigDetail.from_orm(result))


@router.get(
    "/configs/{config}",
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
    "/configs/{config}/json", permissions=[Permission.DomainProblem.view_config]
)
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
    result = schemas.ProblemConfigDataDetail(
        **schemas.ProblemConfigDetail.from_orm(config).dict(), data=data
    )
    return StandardResponse(result)


@router.get(
    "/configs/latest/ls",
    permissions=[Permission.DomainProblem.view_config],
)
async def list_latest_problem_config_objects_under_a_given_prefix(
    problem: models.Problem = Depends(parse_problem),
    after: str = Query("", description="return items after this value"),
    amount: int = Query(100, description="how many items to return"),
    delimiter: str = Query(
        "", description="delimiter used to group common prefixes by"
    ),
    prefix: str = Query("", description="return items prefixed with this value"),
) -> StandardResponse[schemas.ObjectStatsList]:
    config_model = await problem.get_latest_problem_config()
    if config_model is None:
        raise BizError(ErrorCode.ProblemConfigNotFoundError)
    problem_config = LakeFSProblemConfig(problem)
    data = problem_config.ls(
        ref=config_model.commit_id,
        after=after,
        amount=amount,
        delimiter=delimiter,
        prefix=prefix,
    )
    object_stats_list = schemas.ObjectStatsList(**data.to_dict())
    return StandardResponse(object_stats_list)


@router.get(
    "/configs/latest/diff",
    permissions=[Permission.DomainProblem.view_config],
)
async def diff_problem_config_default_branch(
    problem: models.Problem = Depends(parse_problem),
    after: str = Query("", description="return items after this value"),
    amount: int = Query(100, description="how many items to return"),
    delimiter: str = Query(
        "", description="delimiter used to group common prefixes by"
    ),
    prefix: str = Query("", description="return items prefixed with this value"),
) -> StandardResponse[schemas.DiffList]:
    problem_config = LakeFSProblemConfig(problem)
    data = problem_config.diff(
        branch=problem_config.branch_name,
        after=after,
        amount=amount,
        delimiter=delimiter,
        prefix=prefix,
    )
    object_stats_list = schemas.DiffList(**data.to_dict())
    return StandardResponse(object_stats_list)
