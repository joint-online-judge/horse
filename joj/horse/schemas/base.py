import re
from datetime import datetime
from enum import Enum
from functools import lru_cache
from inspect import Parameter, signature
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generator,
    Generic,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)
from uuid import UUID

from fastapi import Depends, Request, params
from fastapi_utils.api_model import APIModel
from fastapi_utils.camelcase import snake2camel
from makefun import wraps
from pydantic import (
    BaseModel as PydanticBaseModel,
    ConstrainedInt,
    ConstrainedStr,
    create_model,
)
from pydantic.datetime_parse import parse_datetime
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.functions import FunctionElement
from sqlalchemy.sql.schema import Column
from sqlalchemy.types import DateTime
from sqlmodel import Field, SQLModel
from starlette.datastructures import MultiDict

from joj.horse.utils.base import is_uuid
from joj.horse.utils.errors import ErrorCode

if TYPE_CHECKING:
    Model = TypeVar("Model", bound="BaseModel")


class BaseModel(APIModel):
    """"""

    class Config:
        validate_all = True


class Operation(Enum):
    Create = "Create"
    Read = "Read"
    Update = "Update"
    Delete = "Delete"


class NoneNegativeInt(ConstrainedInt):
    ge = 0


class PositiveInt(ConstrainedInt):
    gt = 0


class PaginationLimit(PositiveInt):
    le = 500


class LongStr(ConstrainedStr):
    max_length = 256


class NoneEmptyStr(ConstrainedStr):
    min_length = 1


class SearchQueryStr(ConstrainedStr):
    min_length = 2


class NoneEmptyLongStr(LongStr, NoneEmptyStr):
    pass


class UserInputURL(str):
    URL_RE = re.compile(r"[\w-]+", flags=re.ASCII)

    @classmethod
    def __get_validators__(
        cls,
    ) -> Generator[Callable[[Union[str, Any]], str], None, None]:
        yield cls.validate

    @classmethod
    def validate(cls, v: Optional[str]) -> LongStr:
        if not v:
            return LongStr("")
        if is_uuid(v):
            raise ValueError("url can not be uuid")
        if not UserInputURL.URL_RE.fullmatch(v):
            raise ValueError("url can only contains [a-zA-Z0-9_-]")
        return LongStr(v)


class LongText(ConstrainedStr):
    max_length = 65536


class utcnow(FunctionElement):
    type = DateTime()


@compiles(utcnow, "postgresql")
def pg_utcnow(element: Any, compiler: Any, **kwargs: Any) -> str:
    return "TIMEZONE('utc', CURRENT_TIMESTAMP)"


@compiles(utcnow, "mssql")
def ms_utcnow(element: Any, compiler: Any, **kwargs: Any) -> str:
    return "GETUTCDATE()"


def get_datetime_column(**kwargs: Any) -> Column:
    if "index" not in kwargs:
        kwargs["index"] = True
    if "nullable" not in kwargs:
        kwargs["nullable"] = False
    return Column(DateTime(timezone=True), **kwargs)


class UTCDatetime(datetime):
    """parse a datetime and convert in into UTC format"""

    @classmethod
    def __get_validators__(cls) -> Any:
        yield cls.validate

    @classmethod
    def validate(cls, v: Any) -> datetime:
        return datetime.fromtimestamp(parse_datetime(v).timestamp())


class BaseORMSchema(SQLModel, BaseModel):
    pass


class URLORMSchema(BaseORMSchema):
    url: str = Field("", description="(unique) url of the domain")


class URLCreateMixin(BaseModel):
    url: UserInputURL = Field("", description="(unique) url of the domain")


class DomainMixin(BaseModel):
    domain_id: UUID


class IDMixin(BaseModel):
    id: UUID


class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: datetime


BT = TypeVar("BT", bound=PydanticBaseModel)


@lru_cache(maxsize=128)
def get_standard_list_response_sub_model(
    cls: Type[PydanticBaseModel],
) -> Type[PydanticBaseModel]:
    name = cls.__name__
    return create_model(
        f"{name}List",
        count=(int, 0),
        results=(List[cls], []),  # type: ignore
        __base__=BaseModel,
    )


@lru_cache(maxsize=None)
def get_standard_response_model(
    cls: Type[PydanticBaseModel], is_list: bool = False
) -> Tuple[Type[PydanticBaseModel], Optional[Type[PydanticBaseModel]]]:
    name = cls.__name__
    sub_model: Optional[Type[PydanticBaseModel]]
    if is_list:
        model_name = f"{name}ListResp"
        sub_model = get_standard_list_response_sub_model(cls)
        data_type = (Optional[sub_model], None)
    else:
        model_name = f"{name}Resp"
        sub_model = None
        data_type = (Optional[cls], None)
    return (
        create_model(
            model_name,
            error_code=(ErrorCode, ...),
            error_msg=(Optional[str], None),
            data=data_type,
            __base__=BaseModel,
        ),
        sub_model,
    )


class Empty(BaseModel):
    pass


class StandardErrorResponse(BaseModel):
    error_code: ErrorCode
    error_msg: Optional[str] = None
    data: Optional[Any] = None


class StandardResponse(Generic[BT]):
    def __class_getitem__(cls, item: Any) -> Type[Any]:
        return get_standard_response_model(item)[0]

    def __new__(
        cls, data: Union[BT, Type[BT], Empty] = Empty()
    ) -> "StandardResponse[BT]":
        response_type, _ = get_standard_response_model(type(data))  # type: ignore
        response_data = data

        return response_type(  # type: ignore
            error_code=ErrorCode.Success, error_msg=None, data=response_data
        )


class StandardListResponse(Generic[BT]):
    def __class_getitem__(cls, item: Any) -> Type[Any]:
        return get_standard_response_model(item, True)[0]

    def __new__(
        cls,
        results: Optional[List[Union[BT, Type[BT], Empty]]] = None,
        count: Optional[int] = None,
    ) -> "StandardListResponse[BT]":
        if results is None:
            results = []
        data_type = len(results) and type(results[0]) or Empty
        response_type, sub_model_type = get_standard_response_model(
            data_type, True  # type: ignore
        )
        if count is None:
            count = len(results)
        response_data: PydanticBaseModel
        if sub_model_type is None:
            response_data = Empty()
        else:
            response_data = sub_model_type(count=count, results=results)

        return response_type(  # type: ignore
            error_code=ErrorCode.Success, error_msg=None, data=response_data
        )


class LimitOffsetPagination(BaseModel):
    count: int


def camelcase_parameters(func: Any) -> Any:
    func_sig = signature(func)
    parameters = list(func_sig.parameters.values())
    start_index = -1
    for i, parameter in enumerate(parameters):
        if (
            parameter.default
            and isinstance(parameter.default, (params.Query, params.Path))
            and parameter.default.alias is None
        ):
            if start_index < 0:
                start_index = i
            parameter.default.alias = snake2camel(parameter.name, start_lower=True)

    if start_index >= 0:
        parameters.insert(
            start_index,
            Parameter(
                "camelcase_parameters_dependency",
                kind=Parameter.POSITIONAL_OR_KEYWORD,
                default=Depends(camelcase_parameters_dependency),
            ),
        )
    new_sig = func_sig.replace(parameters=parameters)

    @wraps(func, new_sig=new_sig)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if "camelcase_parameters_dependency" in kwargs:
            del kwargs["camelcase_parameters_dependency"]
        return func(*args, **kwargs)

    return wrapper


def camelcase_parameters_dependency(request: Request) -> None:
    query_params = request.query_params
    new_params = MultiDict()
    for k, v in query_params.multi_items():
        if "_" in k:
            camel = snake2camel(k, start_lower=True)
            new_params.append(camel, v)
        else:
            new_params.append(k, v)
    request._query_params = new_params
