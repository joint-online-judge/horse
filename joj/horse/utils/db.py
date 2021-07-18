from enum import Enum
from functools import lru_cache
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient
from motor.motor_gridfs import AgnosticDatabase
from pymongo.errors import CollectionInvalid
from tortoise import Tortoise
from tortoise.contrib.fastapi import HTTPNotFoundError, register_tortoise
from tortoise.exceptions import DoesNotExist, IntegrityError, OperationalError
from umongo.frameworks.motor_asyncio import MotorAsyncIODocument, MotorAsyncIOInstance
from uvicorn.config import logger

from joj.horse.config import settings
from joj.horse.utils.gridfs_hash_storage import GridFSHashStorage

instance = MotorAsyncIOInstance()


async def init_tortoise() -> None:
    tortoise_config = {
        "connections": {
            "default": {
                "engine": "tortoise.backends.asyncpg",
                "credentials": {
                    "host": settings.db_host,
                    "port": settings.db_port,
                    "user": settings.db_user,
                    "password": settings.db_password,
                    "database": settings.db_name,
                },
            },
        },
        "apps": {
            "models": {
                "models": ["joj.horse.models"],
                "default_connection": "default",
            }
        },
    }
    logger.info(
        "Tortoise-ORM engine: %s.",
        tortoise_config["connections"]["default"]["engine"],  # type: ignore
    )
    try:
        await Tortoise.init(config=tortoise_config, _create_db=True, use_tz=True)
        logger.info("Database %s created.", settings.db_name)
    except OperationalError:
        await Tortoise.init(config=tortoise_config, use_tz=True)
        logger.info("Database %s exists.", settings.db_name)

    logger.info("Tortoise-ORM started, %s, %s.", Tortoise._connections, Tortoise.apps)
    if settings.debug:
        logger.info("Tortoise-ORM generating schema.")
        await Tortoise.generate_schemas()


@lru_cache()
def get_db() -> Optional[AgnosticDatabase]:
    return None


#     logger.info("Starting mongodb connection.")
#     client = AsyncIOMotorClient(
#         host=settings.db_host,
#         port=settings.db_port,
#         username=settings.db_username,
#         password=settings.db_password,
#     )
#     db = client.get_database(settings.db_name)
#     instance.set_db(db)
#     return db


class GridFSBucket(str, Enum):
    problem_config = "problem.config"


@lru_cache()
def get_grid_fs(bucket: GridFSBucket) -> GridFSHashStorage:
    return GridFSHashStorage(instance, bucket.value)


# from joj.horse import models
#
# collections: List[Type[MotorAsyncIODocument]] = [
#     models.User,
#     models.Domain,
#     models.DomainInvitation,
#     models.DomainRole,
#     models.DomainUser,
#     models.Record,
#     models.Problem,
#     models.ProblemSet,
#     models.ProblemGroup,
#     models.ProblemConfigMapping,
# ]


# async def ensure_indexes() -> None:
#     db = get_db()
#     for model in collections:
#         collection_name = model.opts.collection_name
#         try:
#             await db.create_collection(collection_name)
#             logger.info(f'Create "{collection_name}".')
#         except CollectionInvalid:
#             pass
#         await model.ensure_indexes()
#         logger.info(f'Ensure indexes for "{collection_name}".')
