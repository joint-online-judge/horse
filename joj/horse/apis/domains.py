from datetime import datetime
from typing import List, Optional

from fastapi import Body, Depends, Query
from tortoise import transactions
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.models.permission import FIXED_ROLES, READONLY_ROLES
from joj.horse.schemas import Empty, StandardListResponse, StandardResponse
from joj.horse.schemas.permission import (
    DEFAULT_DOMAIN_PERMISSION,
    DefaultRole,
    Permission,
)
from joj.horse.utils.auth import Authentication, DomainAuthentication, ensure_permission
from joj.horse.utils.errors import BizError, ErrorCode
from joj.horse.utils.parser import (
    parse_domain,
    parse_domain_invitation,
    parse_domain_role,
    parse_ordering_query,
    parse_pagination_query,
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
    ordering: schemas.OrderingQuery = Depends(parse_ordering_query(["name"])),
    pagination: schemas.PaginationQuery = Depends(parse_pagination_query),
    user: models.User = Depends(parse_user_from_auth),
) -> StandardListResponse[schemas.Domain]:
    """List all domains that the current user has a role."""
    domains, count = await user.find_domains(role, ordering, pagination)
    domains = [schemas.Domain.from_orm(domain) for domain in domains]
    return StandardListResponse(domains, count)


@router.post("", dependencies=[Depends(ensure_permission())])
async def create_domain(
    domain_create: schemas.DomainCreate,
    user: models.User = Depends(parse_user_from_auth),
) -> StandardResponse[schemas.Domain]:
    try:
        async with transactions.in_transaction():
            domain = await models.Domain.create(**domain_create.dict(), owner=user)
            logger.info("domain created: %s", domain)
            domain_user = await models.DomainUser.create(
                domain=domain, user=user, role=str(DefaultRole.ROOT)
            )
            logger.info("domain user created: %s", domain_user)
            for role in DefaultRole:
                # skip fixed roles (judge)
                if role in FIXED_ROLES:
                    continue
                domain_role = await models.DomainRole.create(
                    domain=domain,
                    role=role,
                    permission=DEFAULT_DOMAIN_PERMISSION[role].dict(),
                )
                logger.info("domain role created: %s", domain_role)
    except Exception as e:
        logger.exception(f"domain creation failed: {domain_create.url}")
        raise e
    return StandardResponse(schemas.Domain.from_orm(domain))


@router.get(
    "/{domain}",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.view))],
)
async def get_domain(
    domain: models.Domain = Depends(parse_domain),
) -> StandardResponse[schemas.Domain]:
    # await domain.owner.fetch()
    return StandardResponse(await schemas.Domain.from_tortoise_orm(domain))


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
    await domain.save()
    return StandardResponse(await schemas.Domain.from_tortoise_orm(domain))


@router.post(
    "/{domain}/transfer",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.view))],
)
async def transfer_domain(
    domain_transfer: schemas.DomainTransfer,
    domain: models.Domain = Depends(parse_domain),
    user: models.User = Depends(parse_user_from_auth),
    auth: Authentication = Depends(),
) -> StandardResponse[schemas.Domain]:
    target_user = await parse_uid(domain_transfer.target_user, auth)
    # only domain owner (or site root) can transfer the domain
    if user.id != domain.owner_id and not auth.is_root():
        raise BizError(ErrorCode.DomainNotOwnerError)
    # can not transfer to self
    if domain.owner_id == target_user.id:
        raise BizError(ErrorCode.DomainNotOwnerError)
    domain_user = await models.DomainUser.get_or_none(domain=domain, user=target_user)
    # can only transfer the domain to a root user in the domain
    if not domain_user or domain_user.role != DefaultRole.ROOT:
        raise BizError(ErrorCode.DomainNotRootError)
    domain.owner = target_user
    await domain.save()
    return StandardResponse(schemas.Domain.from_orm(domain))


@router.get(
    "/{domain}/users",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.view))],
)
async def list_domain_users(
    domain: models.Domain = Depends(parse_domain),
) -> StandardListResponse[schemas.DomainUser]:
    users = await domain.users.all()
    domain_users = [schemas.DomainUser.from_orm(user) for user in users]
    return StandardListResponse(domain_users)


@router.post(
    "/{domain}/users",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.edit))],
)
async def add_domain_user(
    domain_user_add: schemas.DomainUserAdd,
    domain: models.Domain = Depends(parse_domain),
    domain_auth: DomainAuthentication = Depends(DomainAuthentication),
) -> StandardResponse[schemas.DomainUser]:
    role = domain_user_add.role
    user = await parse_uid(domain_user_add.user, domain_auth.auth)
    # only root member (or site root) can add root member
    if role == DefaultRole.ROOT and not domain_auth.auth.is_domain_root():
        raise BizError(ErrorCode.DomainNotRootError)
    # add member
    domain_user = await models.DomainUser.add_domain_user(
        domain=domain, user=user, role=role
    )
    return StandardResponse(schemas.DomainUser.from_orm(domain_user))


@router.get(
    "/{domain}/users/{user}",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.view))],
)
async def get_domain_user(
    domain: models.Domain = Depends(parse_domain),
    user: models.User = Depends(parse_user_from_path_or_query),
) -> StandardResponse[schemas.DomainUser]:
    domain_user = await models.DomainUser.get_or_none(domain=domain, user=user)
    if domain_user is None:
        raise BizError(ErrorCode.DomainUserNotFoundError)
    return StandardResponse(schemas.DomainUser.from_orm(domain_user))


@router.delete(
    "/{domain}/users/{user}",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.edit))],
)
async def remove_domain_user(
    domain: models.Domain = Depends(parse_domain),
    user: models.User = Depends(parse_user_from_path_or_query),
    domain_auth: DomainAuthentication = Depends(DomainAuthentication),
) -> StandardResponse[Empty]:
    domain_user = await models.DomainUser.get_or_none(domain=domain, user=user)
    if not domain_user:
        raise BizError(ErrorCode.DomainUserNotFoundError)
    # nobody (including domain owner himself) can remove domain owner
    if domain_user.id == domain.owner_id:
        raise BizError(ErrorCode.DomainNotOwnerError)
    # only root member (or site root) can remove root member
    if domain_user.role == DefaultRole.ROOT and not domain_auth.auth.is_domain_root():
        raise BizError(ErrorCode.DomainNotRootError)
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
    # domain owner must be root member
    if role != DefaultRole.ROOT and domain_auth.auth.is_domain_owner():
        raise BizError(ErrorCode.DomainNotRootError)
    # only root member (or site root) can add root member
    if role == DefaultRole.ROOT and not domain_auth.auth.is_domain_root():
        raise BizError(ErrorCode.DomainNotRootError)
    # update member
    domain_user_model = await models.DomainUser.update_domain_user(
        domain=domain, user=user, role=role
    )
    return StandardResponse(schemas.DomainUser.from_orm(domain_user_model))


@router.get(
    "/{domain}/users/{user}/permission",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.view))],
)
async def get_domain_user_permission(
    domain: models.Domain = Depends(parse_domain),
    user: models.User = Depends(parse_user_from_path_or_query),
) -> StandardResponse[schemas.DomainUserPermission]:
    domain_user = await models.DomainUser.get_or_none(domain=domain, user=user)
    if domain_user is None:
        raise BizError(ErrorCode.DomainUserNotFoundError)
    domain_role = await models.DomainRole.get_or_none(
        domain=domain, role=domain_user.role
    )
    if domain_role is None:
        raise BizError(ErrorCode.DomainRoleNotFoundError)

    domain_user_schema = schemas.DomainUser.from_orm(domain_user)
    permission = schemas.DomainPermission(**domain_role.permission)
    result = schemas.DomainUserPermission(
        **domain_user_schema.dict(), permission=permission
    )
    return StandardResponse(result)


@router.get(
    "/{domain}/roles",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.view))],
)
async def list_domain_roles(
    domain: models.Domain = Depends(parse_domain),
) -> StandardListResponse[schemas.DomainRole]:
    roles = await domain.roles.all()
    domain_roles = [schemas.DomainRole.from_orm(role) for role in roles]
    return StandardListResponse(domain_roles)


@router.post(
    "/{domain}/roles",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.edit))],
)
async def create_domain_role(
    domain_role_create: schemas.DomainRoleCreate,
    domain: models.Domain = Depends(parse_domain),
) -> StandardResponse[schemas.DomainRole]:
    if domain_role_create.role in READONLY_ROLES:
        raise BizError(ErrorCode.DomainRoleReadOnlyError)
    if await models.DomainRole.get_or_none(domain=domain, role=domain_role_create.role):
        raise BizError(ErrorCode.DomainRoleNotUniqueError)
    domain_role = await models.DomainRole.create(
        domain=domain,
        role=domain_role_create.role,
        permission=domain_role_create.permission.dict(),
    )
    return StandardResponse(schemas.DomainRole.from_orm(domain_role))


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
    if await models.DomainUser.get_or_none(domain=domain, role=domain_role.role):
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
        if await models.DomainRole.get_or_none(
            domain=domain, role=domain_role_edit.role
        ):
            raise BizError(ErrorCode.DomainRoleNotUniqueError)
        async with transactions.in_transaction():
            await models.DomainUser.filter(role=domain_role.role).update(
                role=domain_role_edit.role
            )
            domain_role.update_from_schema(domain_role_edit)
            await domain_role.save()
    else:
        domain_role.update_from_schema(domain_role_edit)
        await domain_role.save()
    return StandardResponse(schemas.DomainRole.from_orm(domain_role))


@router.post(
    "/{domain}/invitations",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.edit))],
)
async def create_domain_invitation(
    invitation_create: schemas.DomainInvitationCreate,
    domain: models.Domain = Depends(parse_domain),
) -> StandardResponse[schemas.DomainInvitation]:
    if await models.DomainInvitation.get_or_none(
        domain=domain, code=invitation_create.code
    ):
        raise BizError(ErrorCode.DomainInvitationBadRequestError)
    invitation = await models.DomainInvitation.create(
        **invitation_create.dict(),
        domain=domain,
    )
    return StandardResponse(schemas.DomainInvitation.from_orm(invitation))


@router.delete(
    "/{domain}/invitations/{invitation}",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.edit))],
)
async def delete_domain_invitation(
    invitation: models.DomainInvitation = Depends(parse_domain_invitation),
    domain: models.Domain = Depends(parse_domain),
) -> StandardResponse[Empty]:
    if invitation.domain_id != domain.id:
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
    if invitation.domain_id != domain.id:
        raise BizError(ErrorCode.DomainInvitationBadRequestError)
    invitation.update_from_schema(invitation_edit)
    await invitation.save()
    return StandardResponse(schemas.DomainInvitation.from_orm(invitation))


@router.post("/{domain}/join", dependencies=[Depends(ensure_permission())])
async def join_domain_by_invitation(
    invitation_code: str = Query(...),
    domain: models.Domain = Depends(parse_domain),
    user: models.User = Depends(parse_user_from_auth),
) -> StandardResponse[schemas.DomainUser]:
    # validate the invitation
    invitation_model = await models.DomainInvitation.get_or_none(
        domain=domain, code=invitation_code
    )
    if invitation_model is None or datetime.utcnow() > invitation_model.expire_at:
        raise BizError(ErrorCode.DomainInvitationBadRequestError)
    # add member
    domain_user = await models.DomainUser.add_domain_user(
        domain=domain, user=user, role=invitation_model.role
    )
    return StandardResponse(schemas.DomainUser.from_orm(domain_user))
