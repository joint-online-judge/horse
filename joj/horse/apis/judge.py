from fastapi import Depends
from loguru import logger
from starlette.concurrency import run_in_threadpool

from joj.horse import models, schemas
from joj.horse.schemas.base import Empty, StandardResponse
from joj.horse.schemas.permission import Permission
from joj.horse.services.lakefs import LakeFSProblemConfig, LakeFSRecord
from joj.horse.utils.errors import BizError, ErrorCode
from joj.horse.utils.parser import parse_record_judger, parse_user_from_auth
from joj.horse.utils.router import MyRouter

router = MyRouter()
router_name = "judge"
router_tag = "judge"
router_prefix = "/api/v1"


@router.post("/records/{record}/claim", permissions=[Permission.DomainRecord.judge])
async def claim_record_by_judge(
    judge_claim: schemas.JudgeClaim,
    record: models.Record = Depends(parse_record_judger),
    user: models.User = Depends(parse_user_from_auth),
) -> StandardResponse[schemas.JudgeCredentials]:
    # task_id can only be obtained by listening to the celery task queue
    # we give the worker with task_id the chance to claim the record
    # celery tasks can be retried, only one worker can hold the task_id at the same time
    # if a rejudge is scheduled, task_id changes, so previous task will be ineffective
    # TODO: we probably need a lock to handle race condition of rejudge and claim
    if record.task_id is None or record.task_id != judge_claim.task_id:
        raise BizError(ErrorCode.Error)
    # if record.state not in (schemas.RecordState.queueing, schemas.RecordState.retrying):
    #     raise BizError(ErrorCode.Error)
    # we can mark task failed if no problem config is available
    if record.problem_config is None or record.problem is None:
        raise BizError(ErrorCode.Error)

    # we always reset the state to "fetched", for both first attempt and retries
    record.judger_id = user.id
    record.state = schemas.RecordState.fetched
    await record.save_model()
    logger.info("judger claim record: {}", record)

    # initialize the permission of the judger to lakefs
    # the user have read access to all problems in the problem group,
    # actually only the access to one branch is necessary,
    # but it will create too many policies, so we grant all for simplicity
    # the user have read/write access to all records in the problem,
    # because the judger will write test result to the repo
    await record.fetch_related("problem")
    access_key = await models.UserAccessKey.get_lakefs_access_key(user)
    lakefs_problem_config = LakeFSProblemConfig(record.problem)
    lakefs_record = LakeFSRecord(record.problem, record)

    def sync_func() -> None:
        lakefs_problem_config.ensure_user_policy(user, "read")
        lakefs_record.ensure_user_policy(user, "all")

    await run_in_threadpool(sync_func)

    judge_credentials = schemas.JudgeCredentials(
        access_key_id=access_key.access_key_id,
        secret_access_key=access_key.secret_access_key,
        problem_config_repo_name=lakefs_problem_config.repo_name,
        problem_config_commit_id=record.problem_config.commit_id,
        record_repo_name=lakefs_record.repo_name,
        record_commit_id=record.commit_id,
    )
    return StandardResponse(judge_credentials)


@router.post("/records/{record}/state", permissions=[Permission.DomainRecord.judge])
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


@router.post("/records/{record}/judgment", permissions=[Permission.DomainRecord.judge])
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
