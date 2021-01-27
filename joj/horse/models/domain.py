from typing import Optional

from pymongo import IndexModel

from joj.horse.models.user import UserReference
from joj.horse.odm import Document, Reference


class Domain(Document):
    class Mongo:
        collection = "domains"
        indexes = [
            IndexModel("url", unique=True),
            IndexModel("owner"),
            IndexModel("name"),
        ]

    url: str
    name: str
    owner: UserReference

    gravatar: str = ""
    bulletin: str = ""


class DomainReference(Reference):
    data: Optional[Domain] = None
    reference = Domain
