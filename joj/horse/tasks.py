from celery import Celery

from joj.horse.config import settings

celery_app = Celery(
    "tasks",
    backend="rpc://",
    broker=f"redis://{settings.redis_host}:{settings.redis_port}/0",
)

celery_app.conf.update({"result_persistent": False})


# @celery_app.task(name="joj.horse.compile")
# def compile_task_end(result: str) -> None:
#     pass


if __name__ == "__main__":
    celery_app.worker_main(argv=["worker"])
