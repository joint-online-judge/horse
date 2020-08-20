from bson import ObjectId
from typing import Union
from pymongo import IndexModel, ASCENDING

from joj.horse.odm import Document
from joj.horse.models.user import UserReference


class Domain(Document):
    class Mongo:
        collection = "domains"
        indexes = [
            IndexModel("owner")
        ]

    owner: UserReference
