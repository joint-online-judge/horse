from asyncio import create_task
from typing import Any, Dict

from loguru import logger

from joj.horse import models
from joj.horse.tasks import celery_app


class CeleryWorker:
    def __init__(self, record_model: models.Record, record_schema: models.Record):
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
        task = celery_app.send_task(
            "joj.tiger.compile", args=[self.record_schema.dict()]
        )
        # FIXME: it seems that FastAPI is blocked here
        res = task.get(on_message=self.on_message, propagate=False)
        self.record_model.update(res)
        logger.info(f"problem {self.record_model.id} result receive from celery: {res}")
        await self.record_model.commit()
