from fastapi import Depends
from loguru import logger

from joj.horse import models, schemas
from joj.horse.schemas.base import Empty, StandardResponse
from joj.horse.schemas.permission import Permission
from joj.horse.utils.auth import ensure_permission
from joj.horse.utils.errors import BizError, ErrorCode
from joj.horse.utils.lakefs import get_problem_config_repo_name, get_record_repo_name
from joj.horse.utils.parser import parse_record_judger, parse_user_from_auth
from joj.horse.utils.router import MyRouter

router = MyRouter()
router_name = "judge"
router_tag = "judge"
router_prefix = "/api/v1"


judge_dependency = Depends(ensure_permission(Permission.SiteUser.judge))


@router.get("/key", dependencies=[judge_dependency])
async def get_judge_key(
    user: models.User = Depends(parse_user_from_auth),
) -> StandardResponse[schemas.UserAccessKey]:
    access_key = await models.UserAccessKey.get_lakefs_access_key(user)
    return StandardResponse(access_key)


@router.post("/records/{record}/claim", dependencies=[judge_dependency])
async def claim_record_by_judge(
    record: models.Record = Depends(parse_record_judger),
    user: models.User = Depends(parse_user_from_auth),
) -> StandardResponse[schemas.JudgeClaim]:
    if record.state != schemas.RecordState.queueing:
        raise BizError(ErrorCode.Error)
    if record.problem_config is None or record.problem is None:
        raise BizError(ErrorCode.Error)

    # record.judger_id = user.id
    # record.state = schemas.RecordState.fetched
    # await record.save_model()
    logger.info("judger claim record: {}", record)

    # f99c8699-ff59-4536-b8b3-ccfbbd086b36

    judge_claim = schemas.JudgeClaim(
        problem_config_repo_name=get_problem_config_repo_name(record.problem),
        problem_config_commit_id=record.problem_config.commit_id,
        record_repo_name=get_record_repo_name(record),
        record_commit_id=record.commit_id,
    )
    return StandardResponse(judge_claim)


@router.post("/records/{record}/state", dependencies=[judge_dependency])
async def update_record_state_by_judge(
    record: models.Record = Depends(parse_record_judger),
    user: models.User = Depends(parse_user_from_auth),
) -> StandardResponse[schemas.Record]:
    if record.judger_id != user.id:
        raise BizError(ErrorCode.Error)
    if record.state not in (
        schemas.RecordState.fetched,
        schemas.RecordState.compiling,
        schemas.RecordState.running,
        schemas.RecordState.judging,
    ):
        raise BizError(ErrorCode.Error)
    record.state = schemas.RecordState.fetched
    await record.save_model()
    return StandardResponse(record)


@router.post("/records/{record}/judgment", dependencies=[judge_dependency])
async def submit_record_by_judge(
    record_result: schemas.RecordResult,
    record: models.Record = Depends(parse_record_judger),
    user: models.User = Depends(parse_user_from_auth),
) -> StandardResponse[Empty]:
    if record.state != schemas.RecordState.fetched:
        raise BizError(ErrorCode.Error)

    return StandardResponse()


# @router.post("/records/{record}/cases/http")
# async def http_record_cases(
#     record_case_result: schemas.RecordCaseResult,
#     record: schemas.Record = Depends(parse_record_judger),
#     auth: Authentication = Depends(),
# ) -> StandardResponse[Empty]:
#     if auth.user.role != DefaultRole.JUDGE:
#         raise BizError(ErrorCode.UserNotJudgerError)
#     data = record_case_result.dict()
#     logger.info(f"receive from record cases http: {data}")
#     record.cases[data["index"]].update(data["result"])
#     await record.commit()
#     return StandardResponse()
