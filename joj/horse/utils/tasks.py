from asyncio import create_task
from typing import Any, Dict

from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.tasks import celery_app


class CeleryWorker:
    def __init__(self, record_model: models.Record, record_schema: schemas.Record):
        self.record_model = record_model
        self.record_schema = record_schema

    def on_message(self, body: Dict[str, Any]) -> None:
        if body["status"] != "PROGRESS":
            return
        index = body["result"]["index"]
        result = body["result"]
        del result["index"]
        self.record_model.cases[index].update(result)
        ...  # TODO: commit record here
        logger.info(f"receive from celery: case {index}, {result}")

    async def submit_to_celery(self) -> None:
        self.record_model.update({"status": schemas.RecordStatus.waiting})
        waiting_task = create_task(self.record_model.commit())
        task = celery_app.send_task(
            "joj.tiger.compile", args=[self.record_schema.dict()]
        )
        await waiting_task
        res = task.get(on_message=self.on_message, propagate=False)
        self.record_model.update(res)
        logger.info(f"receive from celery: {res}")
        await self.record_model.commit()