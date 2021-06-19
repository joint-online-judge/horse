from gridfs import GridOut
from pymongo import ASCENDING, IndexModel
from umongo import fields
from umongo.frameworks.motor_asyncio import MotorAsyncIODocument

from joj.horse.models.base import DocumentMixin
from joj.horse.utils.db import GridFSBucket, get_grid_fs, instance


@instance.register
class ProblemConfig(DocumentMixin, MotorAsyncIODocument):
    class Meta:
        collection_name = "problem.configs"
        strict = False
