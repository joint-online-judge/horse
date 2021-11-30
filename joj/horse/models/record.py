from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from celery import Celery
from fastapi import BackgroundTasks
from loguru import logger
from sqlalchemy.schema import Column, ForeignKey
from sqlmodel import Field, Relationship
from sqlmodel.sql.sqltypes import GUID
from starlette.concurrency import run_in_threadpool

from joj.horse.models.base import BaseORMModel
from joj.horse.schemas.problem import ProblemSolutionSubmit, RecordStateMixin
from joj.horse.schemas.record import RecordCodeType, RecordDetail, RecordState
from joj.horse.utils.cache import get_redis_cache
from joj.horse.utils.errors import BizError, ErrorCode
from joj.horse.utils.lakefs import LakeFSRecord

if TYPE_CHECKING:
    from joj.horse.models import Problem, ProblemConfig, ProblemSet, User


class Record(BaseORMModel, RecordDetail, table=True):  # type: ignore[call-arg]
    __tablename__ = "records"
    # __table_args__ = (UniqueConstraint("domain_id", "url"),)

    problem_set_id: Optional[UUID] = Field(
        sa_column=Column(
            GUID, ForeignKey("problem_sets.id", ondelete="SET NULL"), nullable=True
        )
    )
    problem_set: Optional["ProblemSet"] = Relationship(back_populates="records")

    problem_id: Optional[UUID] = Field(
        sa_column=Column(
            GUID, ForeignKey("problems.id", ondelete="SET NULL"), nullable=True
        )
    )
    problem: Optional["Problem"] = Relationship(back_populates="records")

    problem_config_id: Optional[UUID] = Field(
        sa_column=Column(
            GUID, ForeignKey("problem_configs.id", ondelete="SET NULL"), nullable=True
        )
    )
    problem_config: Optional["ProblemConfig"] = Relationship(back_populates="records")

    committer_id: Optional[UUID] = Field(
        sa_column=Column(
            GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        )
    )
    committer: Optional["User"] = Relationship(
        back_populates="committed_records",
        sa_relationship_kwargs={"foreign_keys": "[Record.committer_id]"},
    )

    judger_id: Optional[UUID] = Field(
        sa_column=Column(
            GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        )
    )
    judger: Optional["User"] = Relationship(
        back_populates="judged_records",
        sa_relationship_kwargs={"foreign_keys": "[Record.judger_id]"},
    )

    @classmethod
    async def submit(
        cls,
        *,
        background_tasks: BackgroundTasks,
        celery_app: Celery,
        problem_submit: ProblemSolutionSubmit,
        problem_set: Optional["ProblemSet"],
        problem: "Problem",
        user: "User",
    ) -> "Record":
        problem_config = await problem.get_latest_problem_config()
        if problem_config is None:
            raise BizError(ErrorCode.ProblemConfigNotFoundError)

        if (
            problem_submit.code_type == RecordCodeType.archive
            and problem_submit.file is None
        ):
            raise BizError(ErrorCode.Error)

        problem_set_id = problem_set.id if problem_set else None
        record = cls(
            domain_id=problem.domain_id,
            problem_set_id=problem_set_id,
            problem_id=problem.id,
            problem_config_id=problem_config.id,
            committer_id=user.id,
        )
        key = cls.get_user_latest_record_key(problem_set_id, problem.id, user.id)
        value = RecordStateMixin(record_id=record.id, record_state=record.state)

        await record.save_model(commit=False, refresh=False)
        problem.num_submit += 1
        await problem.save_model(commit=True, refresh=True)
        await record.refresh_model()

        cache = get_redis_cache()
        await cache.set(key, value, namespace="user_latest_records")

        background_tasks.add_task(
            record.upload,
            celery_app=celery_app,
            problem_submit=problem_submit,
            problem=problem,
        )

        return record

    async def upload(
        self,
        celery_app: Celery,
        problem_submit: ProblemSolutionSubmit,
        problem: "Problem",
    ) -> None:
        def sync_func() -> None:
            lakefs_record = LakeFSRecord(problem, self)
            lakefs_record.ensure_branch()

            if problem_submit.code_type == RecordCodeType.archive:
                if problem_submit.file is None:
                    raise BizError(ErrorCode.Error)
                lakefs_record.upload_archive(
                    problem_submit.file.filename, problem_submit.file.file
                )

            commit = lakefs_record.commit(f"record: {self.id}")
            logger.info(commit)
            self.state = RecordState.queueing
            self.commit_id = commit.id

        try:
            await run_in_threadpool(sync_func)
            await self.save_model()
            await self.create_task(celery_app)
            logger.error("upload record success: {}", self)
        except Exception as e:
            logger.error("upload record failed: {}", self)
            logger.exception(e)
            self.state = RecordState.failed
            await self.save_model()

    async def create_task(self, celery_app: Celery) -> None:
        # TODO: create a task in celery with this record
        celery_app.send_task("joj.tiger.compile", args=[self.dict(), ""])

    @classmethod
    def get_user_latest_record_key(
        cls, problem_set_id: Optional[UUID], problem_id: UUID, user_id: UUID
    ) -> str:
        if problem_set_id is None:
            return "problem:{}:user:{}".format(problem_id, user_id)
        return "problem_set:{}:problem:{}:user:{}".format(
            problem_set_id, problem_id, user_id
        )

    @classmethod
    async def get_user_latest_record(
        cls,
        problem_set_id: Optional[UUID],
        problem_id: UUID,
        user_id: UUID,
        use_cache: bool = True,
    ) -> RecordStateMixin:
        cache = get_redis_cache()
        key = cls.get_user_latest_record_key(problem_set_id, problem_id, user_id)
        if use_cache:
            value = await cache.get(key, namespace="user_latest_records")
            try:
                return RecordStateMixin(**value)
            except Exception:  # noqa: E722
                logger.exception("error when loading record from cache:")

        statement = (
            cls.sql_select()
            .where(cls.problem_id == problem_id)
            .where(cls.committer_id == user_id)
            .order_by(cls.created_at.desc())
            .limit(1)
        )
        if problem_set_id is None:
            statement = statement.where(cls.problem_set_id.is_(None))  # type: ignore
        else:
            statement = statement.where(cls.problem_set_id == problem_set_id)
        result = await cls.session_exec(statement)
        record = result.one_or_none()
        if record is None:
            record_state = RecordStateMixin()
        else:
            record_state = RecordStateMixin(
                record_id=record.id, record_state=record.state
            )
        if use_cache:
            await cache.set(key, record_state.dict(), namespace="user_latest_records")
        return record_state

    @classmethod
    async def get_user_latest_records(
        cls, problem_set_id: Optional[UUID], problem_ids: List[UUID], user_id: UUID
    ) -> List[RecordStateMixin]:
        cache = get_redis_cache()
        keys = [
            cls.get_user_latest_record_key(problem_set_id, problem_id, user_id)
            for problem_id in problem_ids
        ]
        values = await cache.multi_get(keys, namespace="user_latest_records")
        record_states = []
        updated_cache_pairs = []
        for i, value in enumerate(values):
            try:
                record_state = RecordStateMixin(**value)
            except Exception:  # noqa: E722
                record_state = await cls.get_user_latest_record(
                    problem_set_id=problem_set_id,
                    problem_id=problem_ids[i],
                    user_id=user_id,
                    use_cache=False,
                )
                updated_cache_pairs.append((keys[i], record_state.dict()))
            record_states.append(record_state)
        if updated_cache_pairs:
            await cache.multi_set(updated_cache_pairs, namespace="user_latest_records")
        logger.info(
            "cache: get {} keys, set {} keys",
            len(problem_ids) - len(updated_cache_pairs),
            len(updated_cache_pairs),
        )
        return record_states
