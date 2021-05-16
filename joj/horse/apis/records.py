import io
from typing import Any, Optional

from bson.objectid import ObjectId
from fastapi import Depends
from fastapi.param_functions import Query
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.schemas.base import Empty, PydanticObjectId, StandardResponse
from joj.horse.schemas.record import ListRecords, RecordCaseResult, RecordResult
from joj.horse.utils.auth import Authentication
from joj.horse.utils.db import get_db
from joj.horse.utils.errors import BizError, ErrorCode
from joj.horse.utils.parser import parse_query, parse_record, parse_uid_or_none
from joj.horse.utils.router import MyRouter

router = MyRouter()
router_name = "records"
router_tag = "record"
router_prefix = "/api/v1"


@router.get("")
async def list_records(
    domain_id: Optional[PydanticObjectId] = Query(None),
    problem_set_id: Optional[PydanticObjectId] = Query(None),
    problem_id: Optional[PydanticObjectId] = Query(None),
    query: schemas.BaseFilter = Depends(parse_query),
    user: models.User = Depends(parse_uid_or_none),
    auth: Authentication = Depends(),
) -> StandardResponse[ListRecords]:
    filter = {}
    if user:
        filter["user"] = auth.user.id
    if domain_id is not None:
        filter["domain"] = ObjectId(domain_id)
    if problem_set_id is not None:
        filter["problem_set"] = ObjectId(problem_set_id)
    if problem_id is not None:
        filter["problem"] = ObjectId(problem_id)
    res = await models.Record.to_schema_list(schemas.Record, filter, query)
    return StandardResponse(ListRecords(results=res))


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


# @router.websocket("/{record}/ws")
# async def websocket_record(
#     record: str, websocket: WebSocket  # TODO: parse_record
# ) -> None:
#     record_model: models.Record = await models.Record.find_by_id(record)
#     if record_model is None:
#         raise BizError(ErrorCode.RecordNotFoundError)
#     await websocket.accept()
#     while True:
#         if data["done"] == True:
#             break
#         data = await websocket.receive_json()
#         logger.info(f"receive from record ws: {data}")
#         result = data["result"]
#         record_model.update(result)
#         await record_model.commit()


# @router.websocket("/{record}/cases/ws")
# async def websocket_record_cases(
#     record: str, websocket: WebSocket  # TODO: parse_record
# ) -> None:
#     record_model: models.Record = await models.Record.find_by_id(record)
#     if record_model is None:
#         raise BizError(ErrorCode.RecordNotFoundError)
#     await websocket.accept()
#     while True:
#         if data["done"] == True:
#             break
#         data = await websocket.receive_json()
#         logger.info(f"receive from record cases ws: {data}")
#         index = data["index"]
#         result = data["result"]
#         record_model.cases[index].update(result)
#         await record_model.commit()


@router.post("/{record}/http")
async def http_record(
    record: str, record_result: RecordResult
) -> StandardResponse[Empty]:  # TODO: parse_record
    record_model: models.Record = await models.Record.find_by_id(record)
    if record_model is None:
        raise BizError(ErrorCode.RecordNotFoundError)
    data = record_result.dict()
    logger.info(f"receive from record http: {data}")
    record_model.update(data)
    await record_model.commit()
    return StandardResponse()


@router.post("/{record}/cases/http")
async def http_record_cases(
    record: str, record_case_result: RecordCaseResult  # TODO: parse_record
) -> StandardResponse[Empty]:
    record_model: models.Record = await models.Record.find_by_id(record)
    if record_model is None:
        raise BizError(ErrorCode.RecordNotFoundError)
    data = record_case_result.dict()
    logger.info(f"receive from record cases http: {data}")
    index = data["index"]
    result = data["result"]
    record_model.cases[index].update(result)
    await record_model.commit()
    return StandardResponse()
