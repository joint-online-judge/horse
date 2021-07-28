from functools import lru_cache
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

from pydantic import (
    BaseModel as PydanticBaseModel,
    ConstrainedInt,
    ConstrainedStr,
    create_model,
)

from joj.horse.utils.base import is_uuid
from joj.horse.utils.errors import ErrorCode

if TYPE_CHECKING:
    Model = TypeVar("Model", bound="BaseModel")


class BaseModel(PydanticBaseModel):
    class Config:
        validate_all = True


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


class NoneEmptyLongStr(LongStr, NoneEmptyStr):
    pass


class UserInputURL(str):
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
        return LongStr(v)


class LongText(ConstrainedStr):
    max_length = 65536


class PydanticObjectId(str):
    pass


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
    )


@lru_cache(maxsize=256)
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
            error_msg=(Optional[str], ...),
            data=data_type,
        ),
        sub_model,
    )


class Empty(PydanticBaseModel):
    pass


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
    class Config:
        orm_mode = True

    count: int
