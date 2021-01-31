from datetime import datetime

from pydantic import BaseModel, validator
from pymongo import ASCENDING, IndexModel

# from joj.horse.models.user import UserReference, UserResponse
from joj.horse.odm import Document, object_id_to_str


class DomainUserResponse(BaseModel):
    id: str
    _normalize_id = validator('id', pre=True, allow_reuse=True)(object_id_to_str)

    domain: str
    # user: Union[str, UserResponse]
    role: str

    join_at: datetime

    @validator("join_at", pre=True, always=True)
    def default_join_at(cls, v, *, values, **kwargs):
        return v or datetime.utcnow()


class DomainUser(Document, DomainUserResponse):
    class Mongo:
        collection = "domain.users"
        indexes = [
            IndexModel("domain"),
            IndexModel("user"),
            IndexModel([("domain", ASCENDING), ("user", ASCENDING)], unique=True),
        ]

    # domain: DomainReference
    # user: UserReference
