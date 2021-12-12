from typing import Any, Optional

from fastapi import Depends

from joj.horse import models, schemas
from joj.horse.schemas.base import StandardListResponse, StandardResponse
from joj.horse.schemas.permission import Permission
from joj.horse.utils.parser import (
    parse_domain_from_auth,
    parse_ordering_query,
    parse_pagination_query,
    parse_problem,
    parse_problem_set,
    parse_record,
    parse_user_from_auth,
)
from joj.horse.utils.router import MyRouter

router = MyRouter()
router_name = "domains/{domain}"
router_tag = "record"
router_prefix = "/api/v1"


@router.get("/records", permissions=[Permission.DomainRecord.view])
async def list_records_in_domain(
    domain: models.Domain = Depends(parse_domain_from_auth),
    problem_set: Optional[models.ProblemSet] = Depends(parse_problem_set),
    problem: Optional[models.Problem] = Depends(parse_problem),
    ordering: schemas.OrderingQuery = Depends(parse_ordering_query()),
    pagination: schemas.PaginationQuery = Depends(parse_pagination_query),
    user: models.User = Depends(parse_user_from_auth),
) -> StandardListResponse[schemas.Record]:
    statement = domain.find_records_statement(user, problem_set, problem)
    records, count = await models.Problem.execute_list_statement(
        statement, ordering, pagination
    )
    return StandardResponse(records, count)


@router.get("/records/{record}")
async def get_record(
    record: schemas.Record = Depends(parse_record),
) -> StandardResponse[schemas.Record]:
    return StandardResponse(schemas.Record.from_orm(record))


@router.get("/records/{record}/code")
async def get_record_code(record: schemas.Record = Depends(parse_record)) -> Any:
    pass
    # mime_types = [
    #     "text/plain",
    #     "application/x-tar",
    #     "application/zip",
    #     "application/vnd.rar",
    # ]
    # gfs = AsyncIOMotorGridFSBucket(get_db())
    # grid_out = await gfs.open_download_stream(record.code)
    # return StreamingResponse(
    #     BytesIO(await grid_out.read()), media_type=mime_types[record.code_type]
    # )


# @router.websocket("/{record}/ws")
# async def websocket_record(
#     record: str, websocket: WebSocket
# ) -> None:
#     record_model: schemas.Record = await schemas.Record.find_by_id(record)
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
#     record: str, websocket: WebSocket
# ) -> None:
#     record_model: schemas.Record = await schemas.Record.find_by_id(record)
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
