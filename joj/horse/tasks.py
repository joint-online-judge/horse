from functools import lru_cache

from celery import Celery
from loguru import logger

from joj.horse.config import settings


@lru_cache
def get_celery_app() -> Celery:
    celery_app = Celery(
        "tasks",
        backend="rpc://",
        broker=f"redis://{settings.redis_host}:{settings.redis_port}/0",
    )
    logger.info(celery_app.conf)
    celery_app.conf.update({"result_persistent": False})

    return celery_app


# @celery_app.task(name="joj.horse.compile")
# def compile_task_end(result: str) -> None:
#     pass


if __name__ == "__main__":
    get_celery_app().worker_main(argv=["worker"])
