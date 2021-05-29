import uuid
from datetime import datetime
from typing import List

from bson import ObjectId
from fastapi import Body, Depends, Query
from marshmallow.exceptions import ValidationError
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.models.permission import (
    DEFAULT_DOMAIN_PERMISSION,
    FIXED_ROLES,
    DefaultRole,
    Permission,
)
from joj.horse.schemas import Empty, StandardResponse
from joj.horse.schemas.base import NoneEmptyLongStr
from joj.horse.schemas.domain_user import ListDomainUsers
from joj.horse.utils.auth import Authentication, DomainAuthentication, ensure_permission
from joj.horse.utils.db import instance
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


@router.get("", dependencies=[Depends(ensure_permission())])
async def list_domains(
    role: List[str] = Query([]),
    query: schemas.BaseQuery = Depends(parse_query),
    auth: Authentication = Depends(),
) -> StandardResponse[ListDomainUsers]:
    """
    List all domains visible to the current user.
    """
    cursor = models.DomainUser.cursor_find_user_domains(auth.user.id, role, query)
    results = await schemas.DomainUser.to_list(cursor)
    return StandardResponse(ListDomainUsers(results=results))


@router.post(
    "", dependencies=[Depends(ensure_permission(Permission.SiteDomain.create))]
)
async def create_domain(
    domain: schemas.DomainCreate, auth: Authentication = Depends()
) -> StandardResponse[schemas.Domain]:
    if ObjectId.is_valid(domain.url):
        raise BizError(ErrorCode.InvalidUrlError)
    none_url = domain.url is None
    if none_url:
        # use a random uuid for empty url, replace it with _id later
        domain.url = NoneEmptyLongStr(uuid.uuid4())
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
                # create domain user for creator
                domain_user_schema = schemas.DomainUser(
                    domain=domain_model.id, user=auth.user.id, role=DefaultRole.ROOT
                )
                domain_user_model = models.DomainUser(**domain_user_schema.to_model())
                await domain_user_model.commit()
                logger.info("domain user created: %s", domain_user_model)
                # create domain roles (admin, user, guest)
                for role in DefaultRole:
                    # skip fixed roles (root, judge)
                    if role in FIXED_ROLES:
                        continue
                    domain_role_schema = schemas.DomainRole(
                        domain=domain_model.id,
                        role=role,
                        permission=DEFAULT_DOMAIN_PERMISSION[role],
                    )
                    domain_role_model = models.DomainRole(
                        **domain_role_schema.to_model()
                    )
                    await domain_role_model.commit()
                    logger.info("domain role created: %s", domain_user_model)

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
        Depends(ensure_permission(Permission.DomainGeneral.view))
    ],
)
async def get_domain(
    domain: models.Domain = Depends(parse_domain_from_auth),
) -> StandardResponse[schemas.Domain]:
    await domain.owner.fetch()
    return StandardResponse(schemas.Domain.from_orm(domain, unfetch_all=False))


@router.delete(
    "/{domain}",
    dependencies=[Depends(ensure_permission(Permission.SiteDomain.delete))],
    deprecated=True,
)
async def delete_domain(
    domain: models.Domain = Depends(parse_domain_from_auth),
) -> StandardResponse[Empty]:
    """
    TODO: finish this part

    tc-imba: delete domain have many side effects, and is not urgent,
             marked it deprecated and implement it later
    """
    raise BizError(ErrorCode.ApiNotImplementedError)


@router.patch(
    "/{domain}",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.edit))],
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
) -> StandardResponse[ListDomainUsers]:
    cursor = models.DomainUser.cursor_join(
        field="user", condition={"domain": domain.id}
    )
    results = await schemas.DomainUser.to_list(cursor)
    return StandardResponse(ListDomainUsers(results=results))


@router.post(
    "/{domain}/members/{uid}",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.edit))],
)
async def add_member_to_domain(
    domain: models.Domain = Depends(parse_domain),
    user: models.User = Depends(parse_uid),
    role: str = Body(DefaultRole.USER),
    domain_auth: DomainAuthentication = Depends(DomainAuthentication),
) -> StandardResponse[schemas.DomainUser]:
    if await models.DomainUser.find_one({"domain": domain.id, "user": user.id}):
        raise BizError(ErrorCode.UserAlreadyInDomainBadRequestError)

    if role == DefaultRole.ROOT:
        # only root can set root role
        if (
            domain_auth.auth.domain_role != DefaultRole.ROOT
            and domain_auth.auth.site_role != DefaultRole.ROOT
        ):
            # TODO: 403 Exception
            raise Exception
    elif not await models.DomainRole.find_one({"domain": domain.id, "role": role}):
        # check domain role
        raise BizError(ErrorCode.DomainRoleNotFoundError)

    domain_user_schema = schemas.DomainUser(
        domain=domain.id, user=user.id, role=DefaultRole.USER
    )
    domain_user_model = models.DomainUser(**domain_user_schema.to_model())
    await domain_user_model.commit()
    return StandardResponse(schemas.DomainUser.from_orm(domain_user_model))


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
