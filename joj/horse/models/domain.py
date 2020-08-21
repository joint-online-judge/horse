from bson import ObjectId
from typing import Optional
from pymongo import IndexModel, ASCENDING

from joj.horse.odm import Document, Reference
from joj.horse.models.user import UserReference


class Domain(Document):
    class Mongo:
        collection = "domains"
        indexes = [
            IndexModel("owner")
        ]

    url: str
    name: str
    owner: UserReference

    gravatar: str = ""
    bulletin: str = ""


class DomainReference(Reference):
    data: Optional[Domain] = None
    reference = Domain
