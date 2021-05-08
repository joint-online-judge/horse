from celery import Celery

celery_app = Celery("tasks", backend="rpc://", broker="pyamqp://localhost//")

celery_app.conf.update({"result_persistent": False})


@celery_app.task(name="joj.horse.compile")
def compile_task_end(result: str) -> None:
    print(result)


if __name__ == "__main__":
    celery_app.worker_main(argv=["worker"])
