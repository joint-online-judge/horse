import uuid
from functools import lru_cache
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generator,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

from bson import ObjectId
from bson.errors import InvalidId
from pydantic import BaseModel, ConstrainedStr, create_model, validator
from umongo.embedded_document import EmbeddedDocumentImplementation
from umongo.frameworks.motor_asyncio import (
    AsyncIOMotorCursor,
    MotorAsyncIODocument,
    MotorAsyncIOReference,
)

from joj.horse.models.base import DocumentMixin
from joj.horse.utils.errors import ErrorCode

if TYPE_CHECKING:
    from pydantic.typing import AbstractSetIntStr, DictIntStrAny, DictStrAny

    Model = TypeVar("Model", bound="BaseModel")


class LongStr(ConstrainedStr):
    max_length = 256


class NoneEmptyStr(ConstrainedStr):
    min_length = 1


class NoneEmptyLongStr(LongStr, NoneEmptyStr):
    pass


class UserInputURL(NoneEmptyLongStr):
    @classmethod
    def __get_validators__(
        cls,
    ) -> Generator[Callable[[Union[str, Any]], str], None, None]:
        yield cls.validate

    @classmethod
    def validate(cls, v: Optional[str]) -> NoneEmptyLongStr:
        if not v:
            return NoneEmptyLongStr(uuid.uuid4())
        if ObjectId.is_valid(v):
            raise ValueError("url can not be ObjectId")
        try:
            uuid.UUID(v)
        except ValueError:
            pass
        else:
            raise ValueError("url can not be uuid")
        return NoneEmptyLongStr(v)


class LongText(ConstrainedStr):
    max_length = 65536


class PydanticObjectId(str):
    @classmethod
    def __get_validators__(
        cls,
    ) -> Generator[Callable[[Union[str, Any]], str], None, None]:
        yield cls.validate

    @classmethod
    def validate(cls, v: Union[str, ObjectId]) -> str:
        try:
            if isinstance(v, str):
                v = ObjectId(v)
            elif not isinstance(v, ObjectId):
                raise InvalidId() from None
        except InvalidId:
            raise TypeError("ObjectId required")
        return str(v)


class BaseODMSchema(BaseModel):
    class Config:
        orm_mode = True

    id: Optional[PydanticObjectId]

    def to_model(
        self,
        *,
        include: Union["AbstractSetIntStr", "DictIntStrAny"] = None,
        exclude: Union["AbstractSetIntStr", "DictIntStrAny"] = None,
    ) -> "DictStrAny":
        document = self.dict(
            by_alias=True, include=include, exclude=exclude, exclude_defaults=True
        )
        if self.id is None:
            document.pop("id", None)
        return document

    @classmethod
    def from_orm(
        cls: Type["Model"], obj: DocumentMixin, unfetch_all: bool = True
    ) -> "Model":
        if unfetch_all:
            obj.unfetch_all()
        return super(BaseODMSchema, cls).from_orm(obj)  # type: ignore

    @classmethod
    def get_model_class(cls: Type["Model"]) -> MotorAsyncIODocument:
        def _import(name: str) -> MotorAsyncIODocument:
            components = name.split(".")
            mod = __import__(components[0])
            for comp in components[1:]:
                mod = getattr(mod, comp)
            return mod

        return _import(f"joj.horse.models.{cls.__name__}")

    @classmethod
    async def to_list(
        cls: Type["Model"],
        cursor: AsyncIOMotorCursor,
        func: Optional[Callable[[Any], "Model"]] = None,
    ) -> List["Model"]:
        def _default_func(x: Any) -> "Model":
            if isinstance(x, dict):
                model = cls.get_model_class()  # type: ignore
                x = model.build_from_mongo(x)
            return cls.from_orm(x, unfetch_all=False)  # type: ignore

        if func is None:
            func = _default_func
        return [func(doc) async for doc in cursor]


# class EmbeddedDocument(Generic[T]):
#     @classmethod
#     def __get_validators__(cls):
#         yield cls.validate
#
#     @classmethod
#     def validate(cls, v: MotorAsyncIOReference):
#         if isinstance(v, str):
#             v = ObjectId(v)
#         if isinstance(v, ObjectId):
#             return str(v)
#         if not isinstance(v, MotorAsyncIOReference):
#             raise TypeError('Not a embedded document')
#         if v.pk is None:
#             raise TypeError('Primary key (_id) not found')
#         return v._document and T(**v._document.dump()) or v.pk

T = TypeVar("T")
ReferenceSchema = Union[PydanticObjectId, T]


def reference_schema_validator(
    field: str, schema_type: Any, each_item: bool = False
) -> Any:
    def wrapped(
        v: MotorAsyncIOReference,
    ) -> Union[PydanticObjectId, Type[BaseODMSchema]]:
        if isinstance(v, MotorAsyncIOReference):
            if v.pk is None:
                raise TypeError("Primary key (_id) not found")
            if isinstance(v.pk, dict):
                _doc = v.document_cls.build_from_mongo(v.pk)
                return schema_type.from_orm(_doc)
            return v._document and schema_type(**v._document.dump()) or v.pk
        return v

    return validator(field, pre=True, allow_reuse=True, each_item=each_item)(wrapped)


def embedded_dict_schema_validator(field: str, each_item: bool = False) -> Any:
    def wrapped(v: EmbeddedDocumentImplementation,) -> Dict[str, Any]:
        if isinstance(v, EmbeddedDocumentImplementation):
            return v.dump()
        return v

    return validator(field, pre=True, allow_reuse=True, each_item=each_item)(wrapped)


BT = TypeVar("BT", bound=BaseModel)


@lru_cache()
def get_standard_response_model(cls: Type[BaseModel]) -> Type[BaseModel]:
    name = cls.__name__
    return create_model(
        f"{name}Resp",
        error_code=(ErrorCode, ...),
        error_msg=(Optional[str], ...),
        data=(Optional[cls], None),
    )


class Empty(BaseModel):
    pass


class StandardResponse(Generic[BT]):
    def __class_getitem__(cls, item: Any) -> Type[Any]:
        return get_standard_response_model(item)

    def __new__(
        cls, data: Union[BT, Type[BT], Empty] = Empty()
    ) -> "StandardResponse[BT]":
        response_type = get_standard_response_model(type(data))  # type: ignore
        response_data = data

        return response_type(  # type: ignore
            error_code=ErrorCode.Success, error_msg=None, data=response_data
        )
