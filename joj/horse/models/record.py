from typing import TYPE_CHECKING, Optional
from uuid import UUID

from celery import Celery
from fastapi import BackgroundTasks
from loguru import logger
from sqlalchemy.schema import Column, ForeignKey
from sqlmodel import Field, Relationship
from sqlmodel.sql.sqltypes import GUID
from starlette.concurrency import run_in_threadpool

from joj.horse.models.base import BaseORMModel
from joj.horse.schemas.problem import ProblemSolutionSubmit
from joj.horse.schemas.record import RecordCodeType, RecordDetail, RecordStatus
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

    user_id: Optional[UUID] = Field(
        sa_column=Column(
            GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        )
    )
    user: Optional["User"] = Relationship(back_populates="records")

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
        record = cls(
            problem_set_id=problem_set.id if problem_set else None,
            problem_id=problem.id,
            user_id=user.id,
        )
        if (
            problem_submit.code_type == RecordCodeType.archive
            and problem_submit.file is None
        ):
            raise BizError(ErrorCode.Error)
        problem.num_submit += 1
        await problem.save_model(commit=False, refresh=False)
        await record.save_model()
        await problem.refresh_model()

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
            self.status = RecordStatus.queueing
            self.commit_id = commit.id

        try:
            await run_in_threadpool(sync_func)
            await self.save_model()
            await self.create_task(celery_app)
        except Exception as e:
            logger.error("upload record failed: {}", self)
            logger.exception(e)
            self.status = RecordStatus.failed
            await self.save_model()

    async def create_task(self, celery_app: Celery) -> None:
        # TODO: create a task in celery with this record
        celery_app.send_task("joj.tiger.compile", args=[self.dict(), ""])
