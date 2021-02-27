from typing import List, Optional

from fastapi import Depends, Query
from fastapi_utils.inferring_router import InferringRouter
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.utils import errors
from joj.horse.utils.auth import Authentication
from joj.horse.utils.db import instance
from joj.horse.utils.parser import parse_record

router = InferringRouter()
router_name = "records"
router_tag = "record"
router_prefix = "/api/v1"


@router.get("/{record}", response_model=schemas.Record)
async def get_record(record: models.Record = Depends(parse_record)) -> schemas.Record:
    return schemas.Record.from_orm(record)


@router.delete("/{record}", status_code=204)
async def delete_record(record: models.Record = Depends(parse_record)):
    await record.delete()
