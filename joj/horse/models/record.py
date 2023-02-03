from typing import TYPE_CHECKING, List, Optional
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
from joj.horse.schemas.record import RecordDetail, RecordPreview, RecordState
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
        if problem_submit.language not in problem.languages:
            raise BizError(ErrorCode.UnsupportedLanguageError)
        problem_set_id = problem_set.id if problem_set else None
        record = cls(
            domain_id=problem.domain_id,
            problem_set_id=problem_set_id,
            problem_id=problem.id,
            problem_config_id=problem_config.id,
            committer_id=user.id,
            language=problem_submit.language,
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
            lakefs_record.upload_multiple_files(
                [file.filename for file in problem_submit.files],
                [file.file for file in problem_submit.files],
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
        result = celery_app.send_task(
            "joj.tiger.task",
            args=[self.dict(), "http://joj-horse:34765"],  # TODO: read from settings
            queue="joj.tiger.official.default",
            task_id=str(self.task_id),
        )
        return result

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
    ) -> Optional[RecordPreview]:
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
        cls, problem_set_id: Optional[UUID], problem_ids: List[UUID], user_id: UUID
    ) -> List[Optional[RecordPreview]]:
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
