from enum import Enum
from functools import lru_cache
from typing import List, Type

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from motor.motor_gridfs import AgnosticDatabase, AgnosticGridFSBucket
from umongo.frameworks.motor_asyncio import MotorAsyncIODocument, MotorAsyncIOInstance
from uvicorn.config import logger

from joj.horse.config import settings
from joj.horse.utils.gridfs_hash_storage import GridFSHashStorage

instance = MotorAsyncIOInstance()


@lru_cache()
def get_db() -> AgnosticDatabase:
    logger.info("Starting mongodb connection.")
    client = AsyncIOMotorClient(
        host=settings.db_host,
        port=settings.db_port,
        username=settings.db_username,
        password=settings.db_password,
    )
    db = client.get_database(settings.db_name)
    instance.set_db(db)
    return db


class GridFSBucket(str, Enum):
    problem_config = "problem.config"


@lru_cache()
def get_grid_fs(bucket: GridFSBucket) -> GridFSHashStorage:
    return GridFSHashStorage(instance, bucket.value)


from joj.horse import models

collections: List[Type[MotorAsyncIODocument]] = [
    models.User,
    models.Domain,
    models.DomainInvitation,
    models.DomainRole,
    models.DomainUser,
    models.Record,
    models.Problem,
    models.ProblemSet,
    models.ProblemGroup,
    models.ProblemConfigMapping,
]


async def ensure_indexes() -> None:
    for model in collections:
        logger.info('Ensure indexes for "%s".' % model.opts.collection_name)
        await model.ensure_indexes()
