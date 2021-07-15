from enum import Enum
from functools import lru_cache
from typing import List, Type

from motor.motor_asyncio import AsyncIOMotorClient
from motor.motor_gridfs import AgnosticDatabase
from pymongo.errors import CollectionInvalid
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
    db = get_db()
    for model in collections:
        collection_name = model.opts.collection_name
        try:
            await db.create_collection(collection_name)
            logger.info(f'Create "{collection_name}".')
        except CollectionInvalid:
            pass
        await model.ensure_indexes()
        logger.info(f'Ensure indexes for "{collection_name}".')
