from joj.horse.schemas.base import BaseODMSchema, EmbeddedSchema, embedded_schema
from joj.horse.schemas.user import UserBase


class Domain(BaseODMSchema):
    url: str
    name: str
    owner: EmbeddedSchema[UserBase]

    gravatar: str = ""
    bulletin: str = ""

    _validate_owner = embedded_schema('owner', UserBase)
