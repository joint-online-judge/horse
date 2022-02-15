from typing import TYPE_CHECKING, List
from uuid import UUID, uuid4

from celery import Celery
from celery.result import AsyncResult
from fastapi import BackgroundTasks
from loguru import logger
from sqlalchemy.schema import Column, ForeignKey
from sqlmodel import Field, Relationship
from sqlmodel.sql.sqltypes import GUID
from starlette.concurrency import run_in_threadpool

from joj.horse.models.base import BaseORMModel
from joj.horse.schemas.cache import get_redis_cache
from joj.horse.schemas.problem import ProblemSolutionSubmit
from joj.horse.schemas.record import (
    RecordCodeType,
    RecordDetail,
    RecordPreview,
    RecordState,
)
from joj.horse.services.lakefs import LakeFSRecord
from joj.horse.utils.errors import BizError, ErrorCode

if TYPE_CHECKING:
    from joj.horse.models import Problem, ProblemConfig, ProblemSet, User


class Record(BaseORMModel, RecordDetail, table=True):  # type: ignore[call-arg]
    __tablename__ = "records"
    # __table_args__ = (UniqueConstraint("domain_id", "url"),)

    domain_id: UUID = Field(
        sa_column=Column(
            GUID, ForeignKey("domains.id", ondelete="CASCADE"), nullable=False
        )
    )
    # domain: "Domain" = Relationship(back_populates="records")

    problem_set_id: UUID | None = Field(
        sa_column=Column(
            GUID, ForeignKey("problem_sets.id", ondelete="SET NULL"), nullable=True
        )
    )
    problem_set: "ProblemSet" | None = Relationship(back_populates="records")

    problem_id: UUID | None = Field(
        sa_column=Column(
            GUID, ForeignKey("problems.id", ondelete="SET NULL"), nullable=True
        )
    )
    problem: "Problem" | None = Relationship(back_populates="records")

    problem_config_id: UUID | None = Field(
        sa_column=Column(
            GUID, ForeignKey("problem_configs.id", ondelete="SET NULL"), nullable=True
        )
    )
    problem_config: "ProblemConfig" | None = Relationship(back_populates="records")

    committer_id: UUID | None = Field(
        sa_column=Column(
            GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        )
    )
    committer: "User" | None = Relationship(
        back_populates="committed_records",
        sa_relationship_kwargs={"foreign_keys": "[Record.committer_id]"},
    )

    judger_id: UUID | None = Field(
        sa_column=Column(
            GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        )
    )
    judger: "User" | None = Relationship(
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
        problem_set: "ProblemSet" | None,
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

        await record.save_model(commit=False, refresh=False)
        problem.num_submit += 1
        await problem.save_model(commit=True, refresh=True)
        await record.refresh_model()

        key = cls.get_user_latest_record_key(problem_set_id, problem.id, user.id)
        value = RecordPreview(
            id=record.id, state=record.state, created_at=record.created_at
        )

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
            self.task_id = uuid4()
            await self.save_model()
            await self.create_task(celery_app)
            logger.info("upload record success: {}", self)
        except Exception as e:
            logger.error("upload record failed: {}", self)
            logger.exception(e)
            self.state = RecordState.failed
            await self.save_model()

    async def create_task(self, celery_app: Celery) -> AsyncResult:
        # create a task in celery with this record
        # TODO: get queue from problem config or somewhere else
        result = celery_app.send_task(
            "joj.tiger.compile",
            args=[self.dict(), ""],
            queue="joj.tiger.official.default",
            task_id=str(self.task_id),
        )
        return result

    @classmethod
    def get_user_latest_record_key(
        cls, problem_set_id: UUID | None, problem_id: UUID, user_id: UUID
    ) -> str:
        if problem_set_id is None:
            return "problem:{}:user:{}".format(problem_id, user_id)
        return "problem_set:{}:problem:{}:user:{}".format(
            problem_set_id, problem_id, user_id
        )

    @classmethod
    async def get_user_latest_record(
        cls,
        problem_set_id: UUID | None,
        problem_id: UUID,
        user_id: UUID,
        use_cache: bool = True,
    ) -> RecordPreview | None:
        cache = get_redis_cache()
        key = cls.get_user_latest_record_key(problem_set_id, problem_id, user_id)
        if use_cache:
            value = await cache.get(key, namespace="user_latest_records")
            try:
                data = value["record"]
                if data is None:
                    return None
                return RecordPreview(**data)
            except (TypeError, ValueError, KeyError):
                pass
            except Exception as e:
                logger.error("error when loading record from cache:")
                logger.exception(e)

        statement = (
            cls.sql_select()
            .where(cls.problem_id == problem_id)
            .where(cls.committer_id == user_id)
            .order_by(cls.created_at.desc())  # type: ignore
            .limit(1)
        )
        if problem_set_id is None:
            statement = statement.where(cls.problem_set_id.is_(None))  # type: ignore
        else:
            statement = statement.where(cls.problem_set_id == problem_set_id)
        result = await cls.session_exec(statement)
        record_model: "Record" = result.one_or_none()
        if record_model is None:
            record = None
        else:
            record = RecordPreview(**record_model.dict())
        if use_cache:
            await cache.set(
                key,
                {"record": record.dict() if record else None},
                namespace="user_latest_records",
            )
        return record

    @classmethod
    async def get_user_latest_records(
        cls, problem_set_id: UUID | None, problem_ids: List[UUID], user_id: UUID
    ) -> List[RecordPreview | None]:
        cache = get_redis_cache()
        keys = [
            cls.get_user_latest_record_key(problem_set_id, problem_id, user_id)
            for problem_id in problem_ids
        ]
        values = []
        if keys:
            values = await cache.multi_get(keys, namespace="user_latest_records")
        records = []
        updated_cache_pairs = []
        for i, value in enumerate(values):
            record = None
            try:
                data = value["record"]
                if data is not None:
                    record = RecordPreview(**data)
                use_cache = True
            except (TypeError, ValueError, KeyError):
                use_cache = False
            except Exception as e:
                use_cache = False
                logger.error("error when loading records from cache:")
                logger.exception(e)
            if not use_cache:
                record = await cls.get_user_latest_record(
                    problem_set_id=problem_set_id,
                    problem_id=problem_ids[i],
                    user_id=user_id,
                    use_cache=False,
                )
                updated_cache_pairs.append((keys[i], record.dict() if record else None))
            records.append(record)
        if updated_cache_pairs:
            await cache.multi_set(updated_cache_pairs, namespace="user_latest_records")
        logger.info(
            "cache: get {} keys, set {} keys",
            len(problem_ids) - len(updated_cache_pairs),
            len(updated_cache_pairs),
        )
        return records
