from functools import lru_cache

from celery import Celery
from loguru import logger

from joj.horse.config import settings


@lru_cache
def get_celery_app() -> Celery:
    backend_url = "rpc://"
    broker_url = "amqp://{}:{}@{}:{}/{}".format(
        settings.rabbitmq_username,
        settings.rabbitmq_password,
        settings.rabbitmq_host,
        settings.rabbitmq_port,
        settings.rabbitmq_vhost,
    )
    celery_app = Celery(
        "tasks",
        backend=backend_url,
        broker=broker_url,
    )
    logger.info(celery_app.conf)
    celery_app.conf.update(
        {
            "result_persistent": False,
            # "task_routes": (
            #     [
            #         ("joj.tiger.*", {"queue": "joj.tiger"}),
            #         # ("joj.horse.*", {"queue": "horse"}),
            #     ],
            # ),
        }
    )

    return celery_app


def celery_app_dependency() -> Celery:
    return get_celery_app()
