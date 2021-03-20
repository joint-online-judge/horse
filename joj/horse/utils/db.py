from functools import lru_cache
from typing import Any, Dict, List, Optional, Type

from motor.motor_asyncio import AsyncIOMotorClient
from umongo.frameworks.motor_asyncio import MotorAsyncIODocument, MotorAsyncIOInstance
from uvicorn.config import logger

from joj.horse.config import settings

instance = MotorAsyncIOInstance()


@lru_cache()
def get_db() -> Any:
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


from joj.horse import models

collections: List[Type[MotorAsyncIODocument]] = [
    models.User,
    models.Domain,
    models.DomainRole,
    models.DomainUser,
    models.Record,
    models.Problem,
    models.ProblemSet,
    models.ProblemGroup,
]


async def ensure_indexes() -> None:
    for model in collections:
        logger.info('Ensure indexes for "%s".' % model.opts.collection_name)
        await model.ensure_indexes()


def generate_join_pipeline(
    field: str, condition: Dict[str, Any], collection: Optional[str] = None
) -> List[Any]:
    if collection is None:
        collection = field + "s"
    return [
        {"$match": condition},
        {
            "$lookup": {
                "from": collection,
                "localField": field,
                "foreignField": "_id",
                "as": field,
            }
        },
        {"$addFields": {field: {"$arrayElemAt": ["$" + field, 0]}}},
    ]
