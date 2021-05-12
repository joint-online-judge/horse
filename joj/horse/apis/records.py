import io
from typing import Any

from fastapi import Depends, WebSocket
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.schemas.base import StandardResponse
from joj.horse.schemas.record import ListRecords
from joj.horse.utils.auth import Authentication
from joj.horse.utils.db import get_db
from joj.horse.utils.errors import BizError, ErrorCode
from joj.horse.utils.parser import parse_record, parse_uid_or_none
from joj.horse.utils.router import MyRouter

router = MyRouter()
router_name = "records"
router_tag = "record"
router_prefix = "/api/v1"


@router.get("")
async def list_records(
    user: models.User = Depends(parse_uid_or_none), auth: Authentication = Depends()
) -> StandardResponse[ListRecords]:
    owner_filter = None
    if user:
        owner_filter = {"owner": auth.user.id}
    return StandardResponse(
        ListRecords(
            results=[
                schemas.Record.from_orm(record)
                async for record in models.Record.find(owner_filter)
            ]
        )
    )


@router.get("/{record}")
async def get_record(
    record: models.Record = Depends(parse_record),
) -> StandardResponse[schemas.Record]:
    return StandardResponse(schemas.Record.from_orm(record))


@router.get("/{record}/code")
async def get_record_code(record: models.Record = Depends(parse_record)) -> Any:
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


@router.websocket("/{record}/ws")
async def websocket_record(
    record: str, websocket: WebSocket  # TODO: parse_record
) -> None:
    record_model: models.Record = await models.Record.find_by_id(record)
    if record_model is None:
        raise BizError(ErrorCode.RecordNotFoundError)
    await websocket.accept()
    while True:
        data = await websocket.receive_json()
        logger.info(f"receive from record ws: {data}")
        result = data["result"]
        record_model.update(result)
        await record_model.commit()
        if data["done"] == True:
            break


@router.websocket("/{record}/cases/ws")
async def websocket_record_cases(
    record: str, websocket: WebSocket  # TODO: parse_record
) -> None:
    record_model: models.Record = await models.Record.find_by_id(record)
    if record_model is None:
        raise BizError(ErrorCode.RecordNotFoundError)
    await websocket.accept()
    while True:
        data = await websocket.receive_json()
        logger.info(f"receive from record cases ws: {data}")
        index = data["index"]
        result = data["result"]
        record_model.cases[index].update(result)
        await record_model.commit()
        if data["done"] == True:
            break
