from typing import Optional
from uuid import UUID

from fastapi import Depends, Query

from joj.horse import models, schemas
from joj.horse.models.permission import PermissionType, ScopeType
from joj.horse.schemas.auth import DomainAuthentication
from joj.horse.schemas.base import StandardListResponse, StandardResponse
from joj.horse.utils.fastapi.router import APIRouter
from joj.horse.utils.parser import (
    parse_domain_from_auth,
    parse_ordering_query,
    parse_pagination_query,
    parse_record,
    parse_user_from_auth,
)

router = APIRouter()
router_name = "domains/{domain}"
router_tag = "record"


@router.get("/records", permissions=[])
async def list_records_in_domain(
    domain: models.Domain = Depends(parse_domain_from_auth),
    domain_auth: DomainAuthentication = Depends(),
    problem_set: Optional[UUID] = Query(None, description="problem set id"),
    problem: Optional[UUID] = Query(None, description="problem id"),
    submitter_id: Optional[UUID] = Query(None, description="submitter uid"),
    ordering: schemas.OrderingQuery = Depends(parse_ordering_query()),
    pagination: schemas.PaginationQuery = Depends(parse_pagination_query),
    user: schemas.User = Depends(parse_user_from_auth),
) -> StandardListResponse[schemas.RecordListDetail]:
    statement = domain.find_records_statement(problem_set, problem, submitter_id)

    if not domain_auth.auth.check(ScopeType.DOMAIN_RECORD, PermissionType.view):
        statement = statement.where(models.Record.committer_id == user.id)

    rows, count = await models.Record.execute_list_statement(
        statement, ordering, pagination
    )
    record_list_details = [schemas.RecordListDetail.from_row(*row) for row in rows]
    return StandardListResponse(record_list_details, count)


@router.get("/records/{record}", permissions=[])
async def get_record(
    record: schemas.RecordDetail = Depends(parse_record),
) -> StandardResponse[schemas.RecordDetail]:
    return StandardResponse(schemas.RecordDetail.from_orm(record))
