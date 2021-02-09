from joj.horse.schemas.base import BaseODMSchema, ReferenceSchema, reference_schema_validator
from joj.horse.schemas.user import UserBase


class Domain(BaseODMSchema):
    url: str
    name: str
    owner: ReferenceSchema[UserBase]

    gravatar: str = ""
    bulletin: str = ""

    _validate_owner = reference_schema_validator('owner', UserBase)
