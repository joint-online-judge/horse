from pymongo import MongoClient

from joj.horse.config import settings

settings.db_name += "-test"
client = MongoClient(
    host=settings.db_host,
    port=settings.db_port,
    username=settings.db_username,
    password=settings.db_password,
)
db = client.get_database(settings.db_name)
client.drop_database(db)
