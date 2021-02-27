from typing import List, Optional

from fastapi import Depends, Query
from fastapi_utils.inferring_router import InferringRouter
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.utils import errors
from joj.horse.utils.auth import Authentication
from joj.horse.utils.db import instance
from joj.horse.utils.parser import parse_record, parse_uid_or_none

router = InferringRouter()
router_name = "records"
router_tag = "record"
router_prefix = "/api/v1"


@router.get("", response_model=List[schemas.Record])
async def list_records(
    user: models.User = Depends(parse_uid_or_none), auth: Authentication = Depends()
) -> List[schemas.Record]:
    owner_filter = None
    if user:
        owner_filter = {"owner": auth.user.id}
    return [
        schemas.Record.from_orm(record)
        async for record in models.Record.find(owner_filter)
    ]


@router.get("/{record}", response_model=schemas.Record)
async def get_record(record: models.Record = Depends(parse_record)) -> schemas.Record:
    return schemas.Record.from_orm(record)


# @router.delete("/{record}", status_code=204)
# async def delete_record(record: models.Record = Depends(parse_record)):
#     await record.delete()
