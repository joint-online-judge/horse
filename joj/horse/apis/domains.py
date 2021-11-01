from datetime import datetime
from typing import List, Optional

from fastapi import Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession
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
from joj.horse.utils.db import db_session_dependency
from joj.horse.utils.errors import BizError, ErrorCode
from joj.horse.utils.parser import (
    parse_domain_from_auth,
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
) -> StandardListResponse[models.Domain]:
    """List all domains that the current user has a role."""
    domains, count = await user.find_domains(role, ordering, pagination)
    domains = [models.Domain.from_orm(domain) for domain in domains]
    return StandardListResponse(domains, count)


@router.post(
    "", dependencies=[Depends(ensure_permission(Permission.SiteDomain.create))]
)
async def create_domain(
    domain_create: models.DomainCreate,
    user: models.UserBase = Depends(parse_user_from_auth),
    session: AsyncSession = Depends(db_session_dependency),
) -> StandardResponse[models.Domain]:
    try:
        domain = models.Domain(**domain_create.dict(), owner_id=user.id)
        session.sync_session.add(domain)
        logger.info("domain created: %s", domain)
        domain_user = models.DomainUser(
            domain_id=domain.id, user_id=user.id, role=str(DefaultRole.ROOT)
        )
        session.sync_session.add(domain_user)
        logger.info("domain user created: %s", domain_user)
        for role in DefaultRole:
            # skip fixed roles (judge)
            if role in FIXED_ROLES:
                continue
            domain_role = models.DomainRole(
                domain_id=domain.id,
                role=role,
                permission=DEFAULT_DOMAIN_PERMISSION[role].dict(),
            )
            session.sync_session.add(domain_role)
            logger.info("domain role created: %s", domain_role)
        await session.commit()
        await session.refresh(domain)
    except Exception as e:
        logger.exception(f"domain creation failed: {domain_create.url}")
        raise e
    return StandardResponse(domain)


@router.get(
    "/{domain}",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.view))],
)
async def get_domain(
    domain: models.Domain = Depends(parse_domain_from_auth),
) -> StandardResponse[models.Domain]:
    # await domain.owner.fetch()
    return StandardResponse(domain)


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
    raise BizError(ErrorCode.APINotImplementedError)


@router.patch(
    "/{domain}",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.edit))],
)
async def update_domain(
    domain_edit: models.DomainEdit,
    domain: models.Domain = Depends(parse_domain_from_auth),
) -> StandardResponse[models.Domain]:
    domain.update_from_schema(domain_edit)
    await domain.save_model()
    return StandardResponse(domain)


@router.post(
    "/{domain}/transfer",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.view))],
)
async def transfer_domain(
    domain_transfer: models.DomainTransfer,
    domain: models.Domain = Depends(parse_domain_from_auth),
    user: models.User = Depends(parse_user_from_auth),
    auth: Authentication = Depends(),
) -> StandardResponse[models.Domain]:
    target_user = await parse_uid(domain_transfer.target_user, auth)
    # only domain owner (or site root) can transfer the domain
    if user.id != domain.owner_id and not auth.is_root():
        raise BizError(ErrorCode.DomainNotOwnerError)
    # can not transfer to self
    if domain.owner_id == target_user.id:
        raise BizError(ErrorCode.DomainNotOwnerError)
    domain_user = await models.DomainUser.get_or_none(
        domain_id=domain.id, user_id=target_user.id
    )
    # can only transfer the domain to a root user in the domain
    if not domain_user or domain_user.role != DefaultRole.ROOT:
        raise BizError(ErrorCode.DomainNotRootError)
    domain.owner_id = target_user.id
    await domain.save_model()
    return StandardResponse(domain)


@router.get(
    "/{domain}/users",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.view))],
)
async def list_domain_users(
    domain: models.Domain = Depends(parse_domain_from_auth),
) -> StandardListResponse[models.DomainUser]:
    users = await domain.users.all()
    domain_users = [models.DomainUser.from_orm(user) for user in users]
    return StandardListResponse(domain_users)


@router.post(
    "/{domain}/users",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.edit))],
)
async def add_domain_user(
    domain_user_add: models.DomainUserAdd,
    domain: models.Domain = Depends(parse_domain_from_auth),
    domain_auth: DomainAuthentication = Depends(DomainAuthentication),
) -> StandardResponse[models.DomainUser]:
    role = domain_user_add.role
    user = await parse_uid(domain_user_add.user, domain_auth.auth)
    # only root member (or site root) can add root member
    if role == DefaultRole.ROOT and not domain_auth.auth.is_domain_root():
        raise BizError(ErrorCode.DomainNotRootError)
    # add member
    domain_user = await models.DomainUser.add_domain_user(
        domain_id=domain.id, user_id=user.id, role=role
    )
    await domain_user.save_model()
    return StandardResponse(domain_user)


@router.get(
    "/{domain}/users/{user}",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.view))],
)
async def get_domain_user(
    domain: models.Domain = Depends(parse_domain_from_auth),
    user: models.User = Depends(parse_user_from_path_or_query),
) -> StandardResponse[models.DomainUser]:
    domain_user = await models.DomainUser.get_or_none(
        domain_id=domain.id, user_id=user.id
    )
    if domain_user is None:
        raise BizError(ErrorCode.DomainUserNotFoundError)
    return StandardResponse(domain_user)


@router.delete(
    "/{domain}/users/{user}",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.edit))],
)
async def remove_domain_user(
    domain: models.Domain = Depends(parse_domain_from_auth),
    user: models.User = Depends(parse_user_from_path_or_query),
    domain_auth: DomainAuthentication = Depends(DomainAuthentication),
) -> StandardResponse[Empty]:
    domain_user = await models.DomainUser.get_or_none(
        domain_id=domain.id, user_id=user.id
    )
    if not domain_user:
        raise BizError(ErrorCode.DomainUserNotFoundError)
    # nobody (including domain owner himself) can remove domain owner
    if domain_user.id == domain.owner_id:
        raise BizError(ErrorCode.DomainNotOwnerError)
    # only root member (or site root) can remove root member
    if domain_user.role == DefaultRole.ROOT and not domain_auth.auth.is_domain_root():
        raise BizError(ErrorCode.DomainNotRootError)
    await domain_user.delete_model()
    return StandardResponse()


@router.patch(
    "/{domain}/users/{user}",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.edit))],
)
async def update_domain_user(
    domain_user_update: models.DomainUserUpdate,
    domain: models.Domain = Depends(parse_domain_from_auth),
    user: models.User = Depends(parse_user_from_path_or_query),
    domain_auth: DomainAuthentication = Depends(DomainAuthentication),
) -> StandardResponse[models.DomainUser]:
    # domain owner must be root member
    role = domain_user_update.role
    if role != DefaultRole.ROOT and domain_auth.auth.is_domain_owner():
        raise BizError(ErrorCode.DomainNotRootError)
    # only root member (or site root) can add root member
    if role == DefaultRole.ROOT and not domain_auth.auth.is_domain_root():
        raise BizError(ErrorCode.DomainNotRootError)
    # update member
    domain_user = await models.DomainUser.update_domain_user(
        domain_id=domain.id, user_id=user.id, role=role
    )
    await domain_user.save_model()
    return StandardResponse(domain_user)


@router.get(
    "/{domain}/users/{user}/permission",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.view))],
)
async def get_domain_user_permission(
    domain: models.Domain = Depends(parse_domain_from_auth),
    user: models.User = Depends(parse_user_from_path_or_query),
) -> StandardResponse[models.DomainUserPermission]:
    domain_user = await models.DomainUser.get_or_none(
        domain_id=domain.id, user_id=user.id
    )
    if domain_user is None:
        raise BizError(ErrorCode.DomainUserNotFoundError)
    domain_role = await models.DomainRole.get_or_none(
        domain_id=domain.id, role=domain_user.role
    )
    if domain_role is None:
        raise BizError(ErrorCode.DomainRoleNotFoundError)

    permission = schemas.DomainPermission(**domain_role.permission)
    result = models.DomainUserPermission(domain_user=domain_user, permission=permission)
    return StandardResponse(result)


@router.get(
    "/{domain}/roles",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.view))],
)
async def list_domain_roles(
    domain: models.Domain = Depends(parse_domain_from_auth),
) -> StandardListResponse[models.DomainRole]:
    roles = await domain.roles.all()
    domain_roles = [models.DomainRole.from_orm(role) for role in roles]
    return StandardListResponse(domain_roles)


@router.post(
    "/{domain}/roles",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.edit))],
)
async def create_domain_role(
    domain_role_create: models.DomainRoleCreate,
    domain: models.Domain = Depends(parse_domain_from_auth),
) -> StandardResponse[models.DomainRole]:
    if domain_role_create.role in READONLY_ROLES:
        raise BizError(ErrorCode.DomainRoleReadOnlyError)
    if await models.DomainRole.get_or_none(
        domain_id=domain.id, role=domain_role_create.role
    ):
        raise BizError(ErrorCode.DomainRoleNotUniqueError)
    domain_role = models.DomainRole(
        domain_id=domain.id,
        role=domain_role_create.role,
        permission=domain_role_create.permission.dict(),
    )
    await domain_role.save_model()
    return StandardResponse(domain_role)


@router.delete(
    "/{domain}/roles/{role}",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.edit))],
)
async def delete_domain_role(
    domain_role: models.DomainRole = Depends(parse_domain_role),
    domain: models.Domain = Depends(parse_domain_from_auth),
    session: AsyncSession = Depends(db_session_dependency),
) -> StandardResponse[Empty]:
    if domain_role.role in READONLY_ROLES:
        raise BizError(ErrorCode.DomainRoleReadOnlyError)
    if await models.DomainUser.get_or_none(domain_id=domain.id, role=domain_role.role):
        raise BizError(ErrorCode.DomainRoleUsedError)
    await domain_role.delete_model()
    return StandardResponse()


@router.patch(
    "/{domain}/roles/{role}",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.edit))],
)
async def update_domain_role(
    domain_role_edit: models.DomainRoleEdit,
    domain_role: models.DomainRole = Depends(parse_domain_role),
    domain: models.Domain = Depends(parse_domain_from_auth),
    session: AsyncSession = Depends(db_session_dependency),
) -> StandardResponse[models.DomainRole]:
    if domain_role_edit.role:
        if (
            domain_role.role in READONLY_ROLES
            or domain_role_edit.role in READONLY_ROLES
        ):
            raise BizError(ErrorCode.DomainRoleReadOnlyError)
        if await models.DomainRole.get_or_none(
            domain_id=domain.id, role=domain_role_edit.role
        ):
            raise BizError(ErrorCode.DomainRoleNotUniqueError)

        domain_users = await models.DomainUser.get_many(
            domain_id=domain.id, role=domain_role.role
        )
        for domain_user in domain_users:
            domain_user.role = domain_role_edit.role
            session.sync_session.add(domain_user)

    domain_role.update_from_schema(domain_role_edit)
    await domain_role.save_model()
    return StandardResponse(domain_role)


@router.post(
    "/{domain}/invitations",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.edit))],
)
async def create_domain_invitation(
    invitation_create: models.DomainInvitationCreate,
    domain: models.Domain = Depends(parse_domain_from_auth),
) -> StandardResponse[models.DomainInvitation]:
    if await models.DomainInvitation.get_or_none(
        domain_id=domain.id, code=invitation_create.code
    ):
        raise BizError(ErrorCode.DomainInvitationBadRequestError)
    invitation = models.DomainInvitation(
        **invitation_create.dict(),
        domain_id=domain.id,
    )
    await invitation.save_model()
    return StandardResponse(invitation)


@router.delete(
    "/{domain}/invitations/{invitation}",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.edit))],
)
async def delete_domain_invitation(
    invitation: models.DomainInvitation = Depends(parse_domain_invitation),
) -> StandardResponse[Empty]:
    await invitation.delete_model()
    return StandardResponse()


@router.patch(
    "/{domain}/invitations/{invitation}",
    dependencies=[Depends(ensure_permission(Permission.DomainGeneral.edit))],
)
async def update_domain_invitation(
    invitation_edit: models.DomainInvitationEdit,
    invitation: models.DomainInvitation = Depends(parse_domain_invitation),
) -> StandardResponse[models.DomainInvitation]:
    invitation.update_from_schema(invitation_edit)
    await invitation.save_model()
    return StandardResponse(invitation)


@router.post("/{domain}/join", dependencies=[Depends(ensure_permission())])
async def join_domain_by_invitation(
    invitation_code: str = Query(...),
    domain: models.Domain = Depends(parse_domain_from_auth),
    user: models.User = Depends(parse_user_from_auth),
) -> StandardResponse[models.DomainUser]:
    # validate the invitation
    invitation_model = await models.DomainInvitation.get_or_none(
        domain_id=domain.id, code=invitation_code
    )
    if invitation_model is None or datetime.utcnow() > invitation_model.expire_at:
        raise BizError(ErrorCode.DomainInvitationBadRequestError)
    # add member
    domain_user = await models.DomainUser.add_domain_user(
        domain_id=domain.id, user_id=user.id, role=invitation_model.role
    )
    return StandardResponse(domain_user)
