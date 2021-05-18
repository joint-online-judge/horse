import time
from datetime import datetime

from bson import ObjectId
from fastapi import Depends, Query
from marshmallow.exceptions import ValidationError
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.models.permission import DefaultRole, PermissionType, ScopeType
from joj.horse.schemas import Empty, StandardResponse
from joj.horse.schemas.domain import ListDomainLabels, ListDomains
from joj.horse.schemas.domain_user import ListDomainMembers
from joj.horse.utils.auth import Authentication, DomainAuthentication, ensure_permission
from joj.horse.utils.db import generate_join_pipeline, instance
from joj.horse.utils.errors import BizError, ErrorCode
from joj.horse.utils.parser import (
    parse_domain,
    parse_domain_from_auth,
    parse_query,
    parse_uid,
)
from joj.horse.utils.router import MyRouter

router = MyRouter()
router_name = "domains"
router_tag = "domain"
router_prefix = "/api/v1"


@router.get("")
async def list_domains(
    query: schemas.BaseFilter = Depends(parse_query), auth: Authentication = Depends()
) -> StandardResponse[ListDomains]:
    """
    List all domains in which {user} has a role.
    Use current login user if {user} is not specified.
    """
    # TODO: finish this part
    # auth.ensure(ScopeType.GENERAL, PermissionType.UNKNOWN)
    filter = {"owner": auth.user.id}
    res = await schemas.Domain.to_list(filter, query)
    return StandardResponse(ListDomains(results=res))


@router.post(
    "",
    dependencies=[
        # Depends(ensure_permission(ScopeType.SITE_DOMAIN, PermissionType.CREATE))
        # TODO: add it back and do it for test user
    ],
)
async def create_domain(
    domain: schemas.DomainCreate, auth: Authentication = Depends()
) -> StandardResponse[schemas.Domain]:
    if ObjectId.is_valid(domain.url):
        raise BizError(ErrorCode.InvalidUrlError)
    none_url = domain.url is None
    if domain.url is None:
        domain.url = str(time.time()).replace(".", "")
    # use transaction for multiple operations
    try:
        async with instance.session() as session:
            async with session.start_transaction():
                domain_schema = schemas.Domain(**domain.dict(), owner=auth.user.id)
                domain_model = models.Domain(**domain_schema.to_model())
                await domain_model.commit()
                if none_url:
                    domain_model.url = str(domain_model.id)
                    await domain_model.commit()
                logger.info("domain created: %s", domain_model)
                domain_user = schemas.DomainUser(
                    domain=domain_model.id, user=auth.user.id, role=DefaultRole.ROOT
                )
                domain_user = models.DomainUser(**domain_user.to_model())
                await domain_user.commit()
                logger.info("domain user created: %s", domain_user)
                # TODO: create domain roles here
    except ValidationError:
        raise BizError(ErrorCode.UrlNotUniqueError)
    except Exception as e:
        logger.error("domain creation failed: %s", domain.url)
        raise e
    return StandardResponse(schemas.Domain.from_orm(domain_model))


@router.get(
    "/{domain}",
    dependencies=[
        # Depends(ensure_permission(ScopeType.SITE_USER, PermissionType.VIEW_HIDDEN)),
        Depends(ensure_permission(ScopeType.DOMAIN_GENERAL, PermissionType.VIEW))
    ],
)
async def get_domain(
    domain: models.Domain = Depends(parse_domain_from_auth),
) -> StandardResponse[schemas.Domain]:
    await domain.owner.fetch()
    return StandardResponse(schemas.Domain.from_orm(domain, unfetch_all=False))


@router.delete(
    "/{domain}",
    dependencies=[
        Depends(ensure_permission(ScopeType.SITE_DOMAIN, PermissionType.DELETE))
    ],
    deprecated=True,
)
async def delete_domain(
    domain: models.Domain = Depends(parse_domain_from_auth),
) -> StandardResponse[Empty]:
    # TODO: finish this part
    # tc-imba: delete domain have many side effects, and is not urgent,
    #          marked it deprecated and implement it later
    raise BizError(ErrorCode.ApiNotImplementedError)
    # await domain.delete()


@router.patch(
    "/{domain}",
    dependencies=[
        Depends(ensure_permission(ScopeType.DOMAIN_GENERAL, PermissionType.EDIT))
    ],
)
async def update_domain(
    domain_edit: schemas.DomainEdit,
    domain: models.Domain = Depends(parse_domain_from_auth),
) -> StandardResponse[schemas.Domain]:
    domain.update_from_schema(domain_edit)
    await domain.commit()
    return StandardResponse(schemas.Domain.from_orm(domain))


@router.get("/{domain}/members")
async def list_members_in_domain(
    domain: models.Domain = Depends(parse_domain),
    auth: DomainAuthentication = Depends(DomainAuthentication),
) -> StandardResponse[ListDomainMembers]:
    pipeline = generate_join_pipeline(field="user", condition={"domain": domain.id})
    return StandardResponse(
        ListDomainMembers(
            results=[
                schemas.DomainUser.from_orm(
                    models.DomainUser.build_from_mongo(domain_user), unfetch_all=False
                )
                async for domain_user in models.DomainUser.aggregate(pipeline)
            ]
        )
    )


@router.post("/{domain}/members/{uid}")
async def add_member_to_domain(
    domain: models.Domain = Depends(parse_domain),
    user: models.User = Depends(parse_uid),
) -> StandardResponse[Empty]:
    if await models.DomainUser.find_one({"domain": domain.id, "user": user.id}):
        raise BizError(ErrorCode.UserAlreadyInDomainBadRequestError)
    domain_user = schemas.DomainUser(
        domain=domain.id, user=user.id, role=DefaultRole.USER
    )
    domain_user = models.DomainUser(**domain_user.to_model())
    await domain_user.commit()
    return StandardResponse()


@router.get("/{domain}/members/join")
async def member_join_in_domain(
    invitation_code: str = Query(...),
    domain: models.Domain = Depends(parse_domain),
    auth: Authentication = Depends(),
) -> StandardResponse[Empty]:
    if await models.DomainUser.find_one({"domain": domain.id, "user": auth.user.id}):
        raise BizError(ErrorCode.UserAlreadyInDomainBadRequestError)
    if (
        invitation_code != domain.invitation_code
        or datetime.utcnow() > domain.invitation_expire_at
    ):
        raise BizError(ErrorCode.DomainInvitationBadRequestError)
    domain_user = schemas.DomainUser(
        domain=domain.id, user=auth.user.id, role=DefaultRole.USER
    )
    domain_user = models.DomainUser(**domain_user.to_model())
    await domain_user.commit()
    return StandardResponse()


@router.delete("/{domain}/members/{uid}")
async def remove_member_from_domain(
    domain: models.Domain = Depends(parse_domain),
    user: models.User = Depends(parse_uid),
) -> StandardResponse[Empty]:
    domain_user = await models.DomainUser.find_one(
        {"domain": domain.id, "user": user.id}
    )
    if domain_user:
        await domain_user.delete()
    return StandardResponse()


@router.get("/{domain}/labels")
async def list_labels_in_domain(
    domain: models.Domain = Depends(parse_domain), auth: Authentication = Depends()
) -> StandardResponse[ListDomainLabels]:
    # TODO: aggregate
    return StandardResponse(
        ListDomainLabels(
            results=[
                label
                async for problem_set in models.ProblemSet.find({"domain": domain.id})
                for label in schemas.ProblemSet.from_orm(problem_set).labels
            ]
        )
    )
