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

from bson import ObjectId
from bson.errors import InvalidId
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


# class BaseODMSchema(BaseModel):
#     class Config:
#         orm_mode = True
#
#     id: Optional[PydanticObjectId]
#
#     def to_model(
#         self,
#         *,
#         include: Union["AbstractSetIntStr", "DictIntStrAny"] = None,
#         exclude: Union["AbstractSetIntStr", "DictIntStrAny"] = None,
#     ) -> "DictStrAny":
#         document = self.dict(
#             by_alias=True, include=include, exclude=exclude, exclude_defaults=True
#         )
#         if self.id is None:
#             document.pop("id", None)
#         return document
#
#     @classmethod
#     def from_orm(
#         cls: Type["Model"], obj: DocumentMixin, unfetch_all: bool = True
#     ) -> "Model":
#         if unfetch_all:
#             obj.unfetch_all()
#         return super(BaseODMSchema, cls).from_orm(obj)  # type: ignore
#
#     @classmethod
#     def get_model_class(cls: Type["Model"]) -> MotorAsyncIODocument:
#         def _import(name: str) -> MotorAsyncIODocument:
#             components = name.split(".")
#             mod = __import__(components[0])
#             for comp in components[1:]:
#                 mod = getattr(mod, comp)
#             return mod
#
#         return _import(f"joj.horse.models.{cls.__name__}")
#
#     @classmethod
#     async def to_list(
#         cls: Type["Model"],
#         cursor: AsyncIOMotorCursor,
#         func: Optional[Callable[[Any], "Model"]] = None,
#     ) -> List["Model"]:
#         def _default_func(x: Any) -> "Model":
#             if isinstance(x, dict):
#                 model = cls.get_model_class()  # type: ignore
#                 x = model.build_from_mongo(x)
#             return cls.from_orm(x, unfetch_all=False)  # type: ignore
#
#         if func is None:
#             func = _default_func
#         return [func(doc) async for doc in cursor]


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

# T = TypeVar("T")
# ReferenceSchema = Union[PydanticObjectId, T]
#
#
# def reference_schema_validator(
#     field: str, schema_type: Any, each_item: bool = False
# ) -> Any:
#     def wrapped(
#         v: MotorAsyncIOReference,
#     ) -> Union[PydanticObjectId, Type[BaseODMSchema]]:
#         if isinstance(v, MotorAsyncIOReference):
#             if v.pk is None:
#                 raise TypeError("Primary key (_id) not found")
#             if isinstance(v.pk, dict):
#                 _doc = v.document_cls.build_from_mongo(v.pk)
#                 return schema_type.from_orm(_doc)
#             return v._document and schema_type(**v._document.dump()) or v.pk
#         return v
#
#     return validator(field, pre=True, allow_reuse=True, each_item=each_item)(wrapped)
#
#
# def embedded_dict_schema_validator(field: str, each_item: bool = False) -> Any:
#     def wrapped(
#         v: EmbeddedDocumentImplementation,
#     ) -> Dict[str, Any]:
#         if isinstance(v, EmbeddedDocumentImplementation):
#             return v.dump()
#         return v
#
#     return validator(field, pre=True, allow_reuse=True, each_item=each_item)(wrapped)


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
