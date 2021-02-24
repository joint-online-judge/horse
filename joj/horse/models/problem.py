from typing import List, Optional

from joj.horse.models.domain import DomainReference
from joj.horse.models.user import UserReference
from joj.horse.odm import Document, Reference


class Problem(Document):
    class Mongo:
        collection = "problems"
        indexes = []

    domain: DomainReference
    owner: UserReference

    title: str
    content: str = ""
    hidden: bool = False
    num_submit: int = 0
    num_accept: int = 0

    data: Optional[int] = None  # modify later
    data_version: int = 2
    languages: List[str] = []


class ProblemReference(Reference):
    data: Optional[Problem] = None
    reference = Problem
