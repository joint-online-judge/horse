from datetime import datetime
from bson import ObjectId
from typing import Union
from pymongo import IndexModel, ASCENDING

from pydantic import validator, BaseModel

from joj.horse.odm import Document
from joj.horse.models.user import UserReference
from joj.horse.models.domain import DomainReference


class Permission(BaseModel):
    """All permissions in a domain"""

    # General
    view: bool = False
    edit_permission: bool = False
    view_mod_badge: bool = True  # what's this?
    edit_description: bool = False

    # Problem
    create_problem: bool = False
    edit_problem: bool = False
    edit_problem_self: bool = True
    view_problem: bool = True
    view_problem_hidden: bool = False
    view_problem_config: bool = False
    view_problem_config_self: bool = True
    submit_problem: bool = True

    
class DomainRole(Document):
    class Mongo:
        collection = "domain.roles"
        indexes = [
            IndexModel("domain"),
            IndexModel("role"),
            IndexModel([("domain", ASCENDING), ("role", ASCENDING)], unique=True),
        ]

    permission: Permission = Permission()

    domain: DomainReference
    role: str
    updated_at: datetime

    @validator("updated_at", pre=True, always=True)
    def default_updated_at(cls, v, *, values, **kwargs):
        return v or datetime.utcnow()
