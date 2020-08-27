from typing import Optional, List

from joj.horse.odm import Document, Reference
from joj.horse.models.domain import DomainReference
from joj.horse.models.user import UserReference
from joj.horse.models.problem import ProblemReference


class ProblemSet(Document):
    class Mongo:
        collection = "problem.sets"
        indexes = [
        ]

    domain: DomainReference
    owner: UserReference

    title: str
    content: str = ""
    hidden: bool = False
    num_submit: int = 0
    num_accept: int = 0

    problems: List[ProblemReference] = []


class ProblemSetReference(Reference):
    data: Optional[ProblemSet] = None
    reference = ProblemSet
