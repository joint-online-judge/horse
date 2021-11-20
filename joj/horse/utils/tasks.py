from asyncio import create_task
from typing import TYPE_CHECKING, Any, Dict

from celery import Celery
from loguru import logger

from joj.horse.tasks import get_celery_app

if TYPE_CHECKING:
    from joj.horse import models, schemas


def celery_app_dependency() -> Celery:
    return get_celery_app()


class CeleryWorker:
    def __init__(self, record_model: "models.Record", record_schema: "schemas.Record"):
        self.record_model = record_model
        self.record_schema = record_schema

    def on_message(self, body: Dict[str, Any]) -> None:
        if body["status"] != "PROGRESS":
            return
        index = body["result"]["index"]
        result = body["result"]
        del result["index"]
        self.record_model.cases[index].update(result)
        create_task(self.record_model.commit())
        logger.info(
            f"problem {self.record_model.id} receive from celery: case {index}, {result}"
        )

    async def submit_to_celery(self) -> None:
        celery_app = get_celery_app()
        task = celery_app.send_task(
            "joj.tiger.compile", args=[self.record_schema.dict()]
        )
        # FIXME: it seems that FastAPI is blocked here
        res = task.get(on_message=self.on_message, propagate=False)
        self.record_model.update(res)
        logger.info(f"problem {self.record_model.id} result receive from celery: {res}")
        await self.record_model.commit()
