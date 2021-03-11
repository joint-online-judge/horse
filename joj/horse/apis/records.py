import io
from typing import List

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.utils import errors
from joj.horse.utils.auth import Authentication
from joj.horse.utils.db import get_db, instance
from joj.horse.utils.parser import parse_record, parse_uid_or_none

router = APIRouter()
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


@router.get("/{record}/code")
async def get_record_code(
    record: models.Record = Depends(parse_record),
) -> StreamingResponse:
    mime_types = [
        "text/plain",
        "application/x-tar",
        "application/zip",
        "application/vnd.rar",
    ]
    gfs = AsyncIOMotorGridFSBucket(get_db())
    grid_out = await gfs.open_download_stream(record.code)
    return StreamingResponse(
        io.BytesIO(await grid_out.read()), media_type=mime_types[record.code_type]
    )
