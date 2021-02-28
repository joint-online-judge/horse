from typing import TYPE_CHECKING, Any, Optional, Type, TypeVar, Union

from bson import ObjectId
from pydantic import BaseModel, validator
from umongo.frameworks.motor_asyncio import MotorAsyncIOReference

if TYPE_CHECKING:
    from pydantic.typing import AbstractSetIntStr, DictIntStrAny, DictStrAny

    Model = TypeVar("Model", bound="BaseModel")


class PydanticObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, str):
            v = ObjectId(v)
        elif not isinstance(v, ObjectId):
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
    def from_orm(cls: Type["Model"], obj: Any, unfetch_all=True) -> "Model":
        if unfetch_all:
            obj.unfetch_all()
        return super(BaseODMSchema, cls).from_orm(obj)  # type: ignore


# class EmbeddedDocument(Generic[T]):
#     @classmethod
#     def __get_validators__(cls):
#         yield cls.validate
#
#     @classmethod
#     def validate(cls, v: MotorAsyncIOReference):
#         print(v)
#         print(cls.__orig_class__.__args__[0])
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


def reference_schema_validator(field, schema_type, each_item=False):
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
