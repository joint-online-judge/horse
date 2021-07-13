from datetime import datetime
from typing import List, Optional

from fastapi import Body, Depends, Query
from marshmallow.exceptions import ValidationError
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.models.permission import (
    DEFAULT_DOMAIN_PERMISSION,
    FIXED_ROLES,
    READONLY_ROLES,
    DefaultRole,
    Permission,
)
from joj.horse.schemas import Empty, StandardResponse
from joj.horse.schemas.domain import ListDomains
from joj.horse.schemas.domain_role import ListDomainRoles
from joj.horse.schemas.domain_user import DomainUserAdd, ListDomainUsers
from joj.horse.utils.auth import Authentication, DomainAuthentication, ensure_permission
from joj.horse.utils.db import instance
from joj.horse.utils.errors import BizError, ErrorCode, ForbiddenError
from joj.horse.utils.parser import (
    parse_domain,
    parse_domain_invitation,
    parse_domain_role,
    parse_query,
    parse_uid,
    parse_user_from_auth,
    parse_user_from_path_or_query,
)
from joj.horse.utils.router import MyRouter

router = MyRouter()
router_name = "domains"
router_tag = "domain"
router_prefix = "/api/v1"


@router.get("", dependencies=[Depends(ensure_permission())])
async def list_domains(
    role: Optional[List[str]] = Query(None),
    query: schemas.BaseQuery = Depends(parse_query),
    user: models.User = Depends(parse_user_from_auth),
) -> StandardResponse[ListDomains]:
    """
    List all domains that the current user has a role.
    """
    cursor = models.DomainUser.cursor_find_user_domains(user, role, query)
    domain_users = await schemas.DomainUser.to_list(cursor)
    results = [x.domain for x in domain_users]
    return StandardResponse(ListDomains(results=results))


@router.post("", dependencies=[Depends(ensure_permission())])
async def create_domain(
    domain: schemas.DomainCreate, user: models.User = Depends(parse_user_from_auth)
) -> StandardResponse[schemas.Domain]:
    # use transaction for multiple operations
    try:
        async with instance.session() as session:
            async with session.start_transaction():
                domain_schema = schemas.Domain(**domain.dict(), owner=user.id)
                domain_model = models.Domain(**domain_schema.to_model())
                await domain_model.commit()
                await domain_model.set_url_from_id()
                logger.info("domain created: %s", domain_model)
                # create domain user for creator
                domain_user_schema = schemas.DomainUser(
                    domain=domain_model.id, user=user.id, role=DefaultRole.ROOT
                )
                domain_user_model = models.DomainUser(**domain_user_schema.to_model())
                await domain_user_model.commit()
                logger.info("domain user created: %s", domain_user_model)
                # create domain roles (root, admin, user, guest)
                for role in DefaultRole:
                    # skip fixed roles (judge)
                    if role in FIXED_ROLES:
                        continue
                    domain_role_schema = schemas.DomainRole(
                        domain=domain_model.id,
                        role=role,
                        permission=DEFAULT_DOMAIN_PERMISSION[role],
                        updated_at=datetime.utcnow(),
                    )
                    domain_role_model = models.DomainRole(
                        **domain_role_schema.to_model()
                    )
                    await domain_role_model.commit()
                    logger.info("domain role created: %s", domain_user_model)

    except ValidationError as e:
        if (
            isinstance(e.messages, Dict)
            and e.messages.get("url") == "Field value must be unique."
        ):
            raise BizError(ErrorCode.UrlNotUniqueError)
        logger.exception(f"domain creation failed: {domain.url}")
        raise e
    except Exception as e:
        logger.exception(f"domain creation failed: {domain.url}")
        raise e
    return StandardResponse(schemas.Domain.from_orm(domain_model))


@router.get(
    "/{domain}",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.view))],
)
async def get_domain(
    domain: models.Domain = Depends(parse_domain),
) -> StandardResponse[schemas.Domain]:
    await domain.owner.fetch()
    return StandardResponse(schemas.Domain.from_orm(domain, unfetch_all=False))


@router.delete(
    "/{domain}",
    dependencies=[Depends(ensure_permission(Permission.SiteDomain.delete))],
    deprecated=True,
)
async def delete_domain(
    domain: models.Domain = Depends(parse_domain),
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
    domain_edit: schemas.DomainEdit, domain: models.Domain = Depends(parse_domain)
) -> StandardResponse[schemas.Domain]:
    domain.update_from_schema(domain_edit)
    await domain.commit()
    return StandardResponse(schemas.Domain.from_orm(domain))


@router.get(
    "/{domain}/users",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.view))],
)
async def list_domain_users(
    domain: models.Domain = Depends(parse_domain),
) -> StandardResponse[ListDomainUsers]:
    cursor = models.DomainUser.cursor_join(
        field="user", condition={"domain": domain.id}
    )
    results = await schemas.DomainUser.to_list(cursor)
    return StandardResponse(ListDomainUsers(results=results))


@router.post(
    "/{domain}/users",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.edit))],
)
async def add_domain_user(
    domain_user_add: DomainUserAdd,
    domain: models.Domain = Depends(parse_domain),
    domain_auth: DomainAuthentication = Depends(DomainAuthentication),
    auth: Authentication = Depends(),
) -> StandardResponse[schemas.DomainUser]:
    role = domain_user_add.role
    user = await parse_uid(domain_user_add.user, auth)
    if role == DefaultRole.ROOT:
        # only root can add root member
        if not domain_auth.auth.is_domain_root():
            raise ForbiddenError()

    # add member
    domain_user_model = await models.DomainUser.add_domain_user(
        domain=domain.id, user=user.id, role=role
    )
    return StandardResponse(schemas.DomainUser.from_orm(domain_user_model))


@router.get(
    "/{domain}/users/{user}",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.view))],
)
async def get_domain_user(
    domain: models.Domain = Depends(parse_domain),
    user: models.User = Depends(parse_user_from_path_or_query),
) -> StandardResponse[schemas.DomainUser]:
    domain_user = await models.DomainUser.find_one(
        {"domain": domain.id, "user": user.id}
    )
    return StandardResponse(schemas.DomainUser.from_orm(domain_user))


@router.delete(
    "/{domain}/users/{user}",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.edit))],
)
async def remove_domain_user(
    domain: models.Domain = Depends(parse_domain),
    user: models.User = Depends(parse_user_from_path_or_query),
) -> StandardResponse[Empty]:
    domain_user = await models.DomainUser.find_one(
        {"domain": domain.id, "user": user.id}
    )
    if not domain_user:
        raise BizError(ErrorCode.DomainUserNotFoundError)
    # can not remove root member
    if domain_user.role == DefaultRole.ROOT:
        raise BizError(ErrorCode.DomainUserRootError)
    await domain_user.delete()
    return StandardResponse()


@router.patch(
    "/{domain}/users/{user}",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.edit))],
)
async def update_domain_user(
    domain: models.Domain = Depends(parse_domain),
    user: models.User = Depends(parse_user_from_path_or_query),
    role: str = Body(DefaultRole.USER),
    domain_auth: DomainAuthentication = Depends(DomainAuthentication),
) -> StandardResponse[schemas.DomainUser]:
    if role == DefaultRole.ROOT:
        # only root can add fixed roles
        if not domain_auth.auth.is_domain_root():
            raise ForbiddenError()

    # update member
    domain_user_model = await models.DomainUser.update_domain_user(
        domain=domain.id, user=user.id, role=role
    )
    return StandardResponse(schemas.DomainUser.from_orm(domain_user_model))


@router.get(
    "/{domain}/roles",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.view))],
)
async def list_domain_roles(
    domain: models.Domain = Depends(parse_domain),
) -> StandardResponse[ListDomainRoles]:
    condition = {"domain": domain.id}
    cursor = models.DomainRole.cursor_find(condition)
    results = await schemas.DomainRole.to_list(cursor)
    return StandardResponse(ListDomainRoles(results=results))


@router.post(
    "/{domain}/roles",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.edit))],
)
async def create_domain_role(
    domain_role: schemas.DomainRoleCreate, domain: models.Domain = Depends(parse_domain)
) -> StandardResponse[schemas.DomainRole]:
    if domain_role.role in READONLY_ROLES:
        raise BizError(ErrorCode.DomainRoleReadOnlyError)
    if await models.DomainRole.find_one(
        {"domain": domain.id, "role": domain_role.role}
    ):
        raise BizError(ErrorCode.DomainRoleNotUniqueError)
    domain_permission = models.DomainPermission()
    domain_permission.update(domain_role.permission)
    domain_role_schema = schemas.DomainRole(
        domain=domain.id, role=domain_role.role, permission=domain_permission.dump()
    )
    domain_role_model = models.DomainRole(**domain_role_schema.to_model())
    await domain_role_model.commit()
    return StandardResponse(schemas.DomainRole.from_orm(domain_role_model))


@router.delete(
    "/{domain}/roles/{role}",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.edit))],
)
async def delete_domain_role(
    domain_role: models.DomainRole = Depends(parse_domain_role),
    domain: models.Domain = Depends(parse_domain),
) -> StandardResponse[Empty]:
    if domain_role.role in READONLY_ROLES:
        raise BizError(ErrorCode.DomainRoleReadOnlyError)
    if await models.DomainUser.find_one(
        {"domain": domain.id, "role": domain_role.role}
    ):
        raise BizError(ErrorCode.DomainRoleUsedError)
    await domain_role.delete()
    return StandardResponse()


@router.patch(
    "/{domain}/roles/{role}",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.edit))],
)
async def update_domain_role(
    domain_role_edit: schemas.DomainRoleEdit,
    domain_role: models.DomainRole = Depends(parse_domain_role),
    domain: models.Domain = Depends(parse_domain),
) -> StandardResponse[schemas.DomainRole]:
    if domain_role_edit.role:
        if (
            domain_role.role in READONLY_ROLES
            or domain_role_edit.role in READONLY_ROLES
        ):
            raise BizError(ErrorCode.DomainRoleReadOnlyError)
        if await models.DomainRole.find_one(
            {"domain": domain.id, "role": domain_role_edit.role}
        ):
            raise BizError(ErrorCode.DomainRoleNotUniqueError)
        async with instance.session() as session:
            async with session.start_transaction():
                condition = {"domain": domain.id, "role": domain_role.role}
                update = {"$set": {"role": domain_role_edit.role}}
                await models.DomainUser.update_many(condition, update)
                domain_role.update_from_schema(domain_role_edit)
                await domain_role.commit()
    else:
        domain_role.update_from_schema(domain_role_edit)
        await domain_role.commit()
    return StandardResponse(schemas.DomainRole.from_orm(domain_role))


@router.post(
    "/{domain}/invitations",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.edit))],
)
async def create_domain_invitation(
    invitation: schemas.DomainInvitationCreate,
    domain: models.Domain = Depends(parse_domain),
) -> StandardResponse[schemas.DomainInvitation]:
    if await models.DomainInvitation.find_one(
        {"domain": domain.id, "code": invitation.code}
    ):
        raise BizError(ErrorCode.DomainInvitationBadRequestError)

    invitation_schema = schemas.DomainInvitation(**invitation.dict(), domain=domain.id)
    invitation_model = models.DomainInvitation(**invitation_schema.to_model())
    await invitation_model.commit()
    return StandardResponse(schemas.DomainInvitation.from_orm(invitation_model))


@router.delete(
    "/{domain}/invitations/{invitation}",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.edit))],
)
async def delete_domain_invitation(
    invitation: models.DomainInvitation = Depends(parse_domain_invitation),
    domain: models.Domain = Depends(parse_domain),
) -> StandardResponse[Empty]:
    if invitation.domain != domain.id:
        raise BizError(ErrorCode.DomainInvitationBadRequestError)
    await invitation.delete()
    return StandardResponse()


@router.patch(
    "/{domain}/invitations/{invitation}",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.edit))],
)
async def update_domain_invitation(
    invitation_edit: schemas.DomainInvitationEdit,
    invitation: models.DomainInvitation = Depends(parse_domain_invitation),
    domain: models.Domain = Depends(parse_domain),
) -> StandardResponse[schemas.DomainInvitation]:
    if invitation.domain != domain.id:
        raise BizError(ErrorCode.DomainInvitationBadRequestError)
    invitation.update_from_schema(invitation_edit)
    await invitation.commit()
    return StandardResponse(schemas.DomainInvitation.from_orm(invitation))


@router.post("/{domain}/join", dependencies=[Depends(ensure_permission())])
async def join_domain_by_invitation(
    invitation_code: str = Query(...),
    domain: models.Domain = Depends(parse_domain),
    user: models.User = Depends(parse_user_from_auth),
) -> StandardResponse[schemas.DomainUser]:
    # validate the invitation
    invitation_model = await models.DomainInvitation.find_one(
        {"domain": domain.id, "code": invitation_code}
    )
    if invitation_model is None or datetime.utcnow() > invitation_model.expire_at:
        raise BizError(ErrorCode.DomainInvitationBadRequestError)
    # add member
    domain_user_model = await models.DomainUser.add_domain_user(
        domain=domain.id, user=user.id, role=invitation_model.role
    )
    return StandardResponse(schemas.DomainUser.from_orm(domain_user_model))
