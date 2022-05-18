from copy import deepcopy
from typing import Any, Dict, List, Optional, cast
from uuid import UUID

from loguru import logger
from pydantic import root_validator
from sqlmodel import Field

from joj.horse.schemas.base import BaseModel, BaseORMSchema, IDMixin, TimestampMixin


class Case(BaseModel):
    time: Optional[str]
    memory: Optional[str]
    score: Optional[int]
    category: Optional[str]
    execute_files: Optional[List[str]]
    execute_args: Optional[List[str]]
    execute_input_file: Optional[str]
    execute_output_file: Optional[str]


class LanguageDefault(BaseModel):
    compile_files: Optional[List[str]]
    compile_args: Optional[List[str]]
    case_default: Optional[Case]
    cases: Optional[List[Case]]


class Language(LanguageDefault):
    name: str


class ProblemConfigJson(BaseModel):
    languages: List[Language]
    language_default: Optional[LanguageDefault]

    @root_validator
    def validate_config(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        old_values = deepcopy(values)
        values["languages"] = [language.dict() for language in values["languages"]]
        if values.get("language_default"):
            values["language_default"] = values["language_default"].dict()
        logger.debug(f"original config values: {values}")
        for i, language in enumerate(values["languages"]):
            if values.get("language_default"):
                language = {
                    **values["language_default"],
                    **{k: v for k, v in language.items() if v is not None},
                }
            if language["cases"] is None:
                language["cases"] = []
            cases = cast(List[Dict[str, Any]], language["cases"])
            for j, case in enumerate(cases):
                if language.get("case_default"):
                    cases[j] = {
                        **language["case_default"],
                        **{k: v for k, v in case.items() if v is not None},
                    }
            values["languages"][i] = language
        logger.debug(f"parsed config values: {values}")
        for i, language in enumerate(values["languages"]):
            for j, case in enumerate(language["cases"]):
                required_fields = [
                    "time",
                    "memory",
                    "score",
                    "category",
                    "execute_files",
                    "execute_args",
                    "execute_input_file",
                    "execute_output_file",
                ]
                for field in required_fields:
                    if case.get(field) is None:
                        raise ValueError(
                            f"languages[{i}].cases[{j}] missing field {field}"
                        )
        return old_values


class ProblemConfigBase(BaseORMSchema):
    commit_message: str = Field(
        "", nullable=False, sa_column_kwargs={"server_default": ""}
    )
    data_version: int = Field(
        2, nullable=False, sa_column_kwargs={"server_default": "2"}
    )


class ProblemConfigCommit(BaseModel):
    message: str = ""
    data_version: int = 2


class ProblemConfig(ProblemConfigBase, IDMixin):
    commit_id: str = Field("", nullable=False, sa_column_kwargs={"server_default": ""})
    committer_id: Optional[UUID] = None


class ProblemConfigDetail(TimestampMixin, ProblemConfig):
    pass


class ProblemConfigDataDetail(ProblemConfigDetail):
    data: ProblemConfigJson
