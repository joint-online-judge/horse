from copy import deepcopy
from enum import Enum

from fastapi import Depends
from loguru import logger
from pydantic.fields import Undefined
from starlette.concurrency import run_in_threadpool

from joj.horse import models, schemas
from joj.horse.schemas.base import Empty, NoneNegativeInt, StandardResponse
from joj.horse.schemas.permission import Permission
from joj.horse.services.lakefs import LakeFSProblemConfig, LakeFSRecord
from joj.horse.utils.errors import BizError, ErrorCode
from joj.horse.utils.fastapi.router import MyRouter
from joj.horse.utils.lock import lock_record_judger
from joj.horse.utils.parser import parse_record_judger, parse_user_from_auth

router = MyRouter()
router_name = "domains/{domain}"
router_tag = "judge"


@router.post(
    "/records/{record}/judge/claim", permissions=[Permission.DomainRecord.judge]
)
async def claim_record_by_judger(
    judger_claim: schemas.JudgerClaim,
    record: models.Record = Depends(parse_record_judger),
    user: models.User = Depends(parse_user_from_auth),
) -> StandardResponse[schemas.JudgerCredentials]:
    # task_id can only be obtained by listening to the celery task queue
    # we give the worker with task_id the chance to claim the record
    # celery tasks can be retried, only one worker can hold the task_id at the same time
    # if a rejudge is scheduled, task_id changes, so previous task will be ineffective
    # TODO: we probably need a lock to handle race condition of rejudge and claim
    if record.task_id is None or str(record.task_id) != judger_claim.task_id:
        raise BizError(ErrorCode.Error)
    # if record.state not in (schemas.RecordState.queueing, schemas.RecordState.retrying):
    #     raise BizError(ErrorCode.Error)
    # we can mark task failed if no problem config is available
    if record.problem_config is None or record.problem is None:
        raise BizError(ErrorCode.Error)

    # we always reset the state to "fetched", for both first attempt and retries
    record.judger_id = user.id
    record.state = schemas.RecordState.fetched

    # initialize the permission of the judger to lakefs
    # the user have read access to all problems in the problem group,
    # actually only the access to one branch is necessary,
    # but it will create too many policies, so we grant all for simplicity
    # originally, the user have read/write access to all records in the problem,
    # because the judger will write test result to the repo
    # now it only have read access
    await record.fetch_related("problem")
    lakefs_problem_config = LakeFSProblemConfig(record.problem)
    lakefs_record = LakeFSRecord(record.problem, record)

    def sync_func() -> None:
        lakefs_problem_config.ensure_user_policy(user, "read")
        lakefs_record.ensure_user_policy(user, "read")

    await run_in_threadpool(sync_func)

    judger_credentials = schemas.JudgerCredentials(
        problem_config_repo_name=lakefs_problem_config.repo_name,
        problem_config_commit_id=record.problem_config.commit_id,
        record_repo_name=lakefs_record.repo_name,
        record_commit_id=record.commit_id,
    )
    return StandardResponse(judger_credentials)


@router.put(
    "/records/{record}/judge",
    permissions=[Permission.DomainRecord.judge],
    dependencies=[Depends(lock_record_judger)],
)
async def submit_record_by_judger(
    record_result: schemas.RecordSubmit = Depends(schemas.RecordSubmit.edit_dependency),
    record: models.Record = Depends(parse_record_judger),
) -> StandardResponse[Empty]:
    # TODO: check current record state
    # if record.state != schemas.RecordState.fetched:
    #     raise BizError(ErrorCode.Error)
    record.update_from_dict(record_result.dict())
    await record.save_model()
    return StandardResponse()


@router.put(
    "/records/{record}/cases/{index}/judge",
    permissions=[Permission.DomainRecord.judge],
    dependencies=[Depends(lock_record_judger)],
)
async def submit_case_by_judger(
    index: NoneNegativeInt,
    record_case_result: schemas.RecordCaseSubmit = Depends(
        schemas.RecordCaseSubmit.edit_dependency
    ),
    record: models.Record = Depends(parse_record_judger),
    user: models.User = Depends(parse_user_from_auth),
) -> StandardResponse[Empty]:
    # TODO: check current record state
    # if record.state != schemas.RecordState.fetched:
    #     raise BizError(ErrorCode.Error)
    length_diff = index - len(record.cases) + 1
    record.time_ms = 0
    record.memory_kb = 0
    record.score = 0
    record.cases = deepcopy(record.cases)  # make sqlalchemy modify the model
    logger.debug(
        f"{user.username} submit case {index} of record {record.id} cases before: {record.cases}"
    )
    if length_diff > 0:
        record.cases.extend([schemas.RecordCase().dict() for _ in range(length_diff)])
    for k, v in record_case_result.dict().items():
        if v is not Undefined:
            if isinstance(v, (str, Enum)):
                v = str(v)
            record.cases[index][k] = v
    for new_case in record.cases:
        record.time_ms += new_case["time_ms"]
        record.memory_kb += new_case["memory_kb"]
        record.score += new_case["score"]
    await record.save_model()
    logger.debug(
        f"{user.username} submit case {index} of record {record.id} cases after: {record.cases}"
    )
    return StandardResponse()
