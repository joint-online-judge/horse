from motor.motor_asyncio import AsyncIOMotorClient

from joj.horse.config import settings

settings.db_name += "-test"
client = AsyncIOMotorClient(
    host=settings.db_host,
    port=settings.db_port,
    username=settings.db_username,
    password=settings.db_password,
)
db = client.get_database(settings.db_name)
client.drop_database(db)
