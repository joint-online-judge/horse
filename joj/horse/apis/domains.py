from datetime import datetime, timezone
from typing import List, Optional

import sqlalchemy.exc
from fastapi import Depends, Query
from loguru import logger
from pydantic.fields import Undefined
from sqlmodel.ext.asyncio.session import AsyncSession

from joj.horse import models, schemas
from joj.horse.models.permission import (
    FIXED_ROLES,
    READONLY_ROLES,
    PermissionType,
    ScopeType,
)
from joj.horse.schemas import Empty, StandardListResponse, StandardResponse
from joj.horse.schemas.auth import Authentication, DomainAuthentication
from joj.horse.schemas.base import SearchQueryStr
from joj.horse.schemas.permission import (
    DEFAULT_DOMAIN_PERMISSION,
    DefaultRole,
    Permission,
)
from joj.horse.services.db import db_session_dependency
from joj.horse.utils.errors import BizError, ErrorCode, UnauthorizedError
from joj.horse.utils.parser import (
    parse_domain_from_auth,
    parse_domain_invitation,
    parse_domain_role,
    parse_domain_without_validation,
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


@router.get("", permissions=[])
async def list_domains(
    role: Optional[List[str]] = Query(None),
    ordering: schemas.OrderingQuery = Depends(parse_ordering_query()),
    pagination: schemas.PaginationQuery = Depends(parse_pagination_query),
    user: models.User = Depends(parse_user_from_auth),
) -> StandardListResponse[schemas.Domain]:
    """List all domains that the current user has a role."""
    statement = user.find_domains_statement(role)
    domains, count = await models.Domain.execute_list_statement(
        statement, ordering, pagination
    )
    return StandardListResponse(domains, count)


@router.post("", permissions=[Permission.SiteDomain.create])
async def create_domain(
    domain_create: schemas.DomainCreate,
    user: models.User = Depends(parse_user_from_auth),
    session: AsyncSession = Depends(db_session_dependency),
) -> StandardResponse[schemas.Domain]:
    try:
        domain = models.Domain(**domain_create.dict(), owner_id=user.id)
        session.sync_session.add(domain)
        logger.info(f"create domain: {domain}")
        domain_user = models.DomainUser(
            domain_id=domain.id, user_id=user.id, role=str(DefaultRole.ROOT)
        )
        session.sync_session.add(domain_user)
        logger.info(f"create domain user: {domain_user}")
        for role in DefaultRole:
            # skip fixed roles (judge)
            if role in FIXED_ROLES:
                continue
            domain_role = models.DomainRole(
                domain_id=domain.id,
                role=role,
                permission=DEFAULT_DOMAIN_PERMISSION[role].dict(),
            )
            logger.info(f"create domain role: {domain_role}")
            session.sync_session.add(domain_role)
        await session.commit()
        await session.refresh(domain)
    except sqlalchemy.exc.IntegrityError as e:
        raise e
    except Exception as e:
        logger.exception(f"domain creation failed: {domain_create.url}")
        raise e
    return StandardResponse(domain)


@router.get("/{domain}", permissions=[Permission.DomainGeneral.view])
async def get_domain(
    domain: models.Domain = Depends(parse_domain_from_auth),
) -> StandardResponse[schemas.DomainDetail]:
    # await domain.owner.fetch()
    return StandardResponse(domain)


@router.delete(
    "/{domain}",
    permissions=[Permission.SiteDomain.delete],
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
    permissions=[Permission.DomainGeneral.edit | Permission.SiteDomain.edit],
)
async def update_domain(
    domain_edit: schemas.DomainEdit = Depends(schemas.DomainEdit.edit_dependency),
    domain: models.Domain = Depends(parse_domain_from_auth),
    domain_auth: DomainAuthentication = Depends(),
) -> StandardResponse[schemas.Domain]:
    if domain_edit.tag is not Undefined:
        if not domain_auth.auth.check(ScopeType.SITE_DOMAIN, PermissionType.edit):
            raise UnauthorizedError("only user with SiteDomain.edit can update tag")

    domain.update_from_dict(domain_edit.dict())
    logger.info(f"update domain: {domain}")
    await domain.save_model()
    return StandardResponse(domain)


@router.post("/{domain}/transfer", permissions=[Permission.DomainGeneral.view])
async def transfer_domain(
    domain_transfer: schemas.DomainTransfer,
    domain: models.Domain = Depends(parse_domain_from_auth),
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
    domain_user = await models.DomainUser.get_or_none(
        domain_id=domain.id, user_id=target_user.id
    )
    # can only transfer the domain to a root user in the domain
    if not domain_user or domain_user.role != DefaultRole.ROOT:
        raise BizError(ErrorCode.DomainNotRootError)
    domain.owner_id = target_user.id
    logger.info(
        f"transfer domain: ({user.username} -> {target_user.username}) {domain}"
    )
    await domain.save_model()
    return StandardResponse(domain)


@router.get("/{domain}/users", permissions=[Permission.DomainGeneral.view])
async def list_domain_users(
    domain: models.Domain = Depends(parse_domain_from_auth),
    ordering: schemas.OrderingQuery = Depends(parse_ordering_query()),
    pagination: schemas.PaginationQuery = Depends(parse_pagination_query),
) -> StandardListResponse[schemas.UserWithDomainRole]:
    statement = domain.find_domain_users_statement()
    rows, count = await models.DomainUser.execute_list_statement(
        statement, ordering, pagination
    )
    domain_users = [schemas.UserWithDomainRole.from_domain_user(*row) for row in rows]
    return StandardListResponse(domain_users, count)


@router.post("/{domain}/users", permissions=[Permission.DomainGeneral.edit])
async def add_domain_user(
    domain_user_add: schemas.DomainUserAdd,
    domain: models.Domain = Depends(parse_domain_from_auth),
    domain_auth: DomainAuthentication = Depends(DomainAuthentication),
) -> StandardResponse[schemas.UserWithDomainRole]:
    role = domain_user_add.role
    # only root member (or site root) can add root member
    if role == DefaultRole.ROOT and not domain_auth.auth.is_domain_root():
        raise BizError(ErrorCode.DomainNotRootError)
    user = await parse_uid(domain_user_add.user, domain_auth.auth)
    user_dict = user.dict()
    # add member
    domain_user = await models.DomainUser.add_domain_user(
        domain_id=domain.id, user_id=user.id, role=role
    )
    logger.info(f"create domain user: {domain_user}")
    await domain_user.save_model()
    return StandardResponse(
        schemas.UserWithDomainRole.from_domain_user(domain_user, user_dict)
    )


@router.get("/{domain}/users/{user}", permissions=[Permission.DomainGeneral.view])
async def get_domain_user(
    domain: models.Domain = Depends(parse_domain_from_auth),
    user: models.User = Depends(parse_user_from_path_or_query),
) -> StandardResponse[schemas.UserWithDomainRole]:
    domain_user = await models.DomainUser.get_or_none(
        domain_id=domain.id, user_id=user.id
    )
    if domain_user is None:
        raise BizError(ErrorCode.DomainUserNotFoundError)
    return StandardResponse(
        schemas.UserWithDomainRole.from_domain_user(domain_user, user)
    )


@router.delete("/{domain}/users/{user}", permissions=[Permission.DomainGeneral.edit])
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
    logger.info(f"delete domain user: {domain_user}")
    await domain_user.delete_model()
    return StandardResponse()


@router.patch("/{domain}/users/{user}", permissions=[Permission.DomainGeneral.edit])
async def update_domain_user(
    domain_user_update: schemas.DomainUserUpdate,
    domain: models.Domain = Depends(parse_domain_from_auth),
    user: models.User = Depends(parse_user_from_path_or_query),
    domain_auth: DomainAuthentication = Depends(DomainAuthentication),
) -> StandardResponse[schemas.UserWithDomainRole]:
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
    logger.info(f"update domain user: {domain_user}")
    await domain_user.save_model()
    return StandardResponse(
        schemas.UserWithDomainRole.from_domain_user(domain_user, user)
    )


@router.get(
    "/{domain}/users/{user}/permission", permissions=[Permission.DomainGeneral.view]
)
async def get_domain_user_permission(
    domain: models.Domain = Depends(parse_domain_from_auth),
    user: models.User = Depends(parse_user_from_path_or_query),
) -> StandardResponse[schemas.DomainUserPermission]:
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
    result = schemas.DomainUserPermission(
        **domain_user.dict(),
        permission=permission,
    )
    return StandardResponse(result)


@router.get("/{domain}/candidates", permissions=[Permission.DomainGeneral.edit])
async def search_domain_candidates(
    domain: models.Domain = Depends(parse_domain_from_auth),
    ordering: schemas.OrderingQuery = Depends(parse_ordering_query(["username"])),
    query: SearchQueryStr = Query(..., description="search query"),
) -> StandardListResponse[schemas.UserWithDomainRole]:
    pagination = schemas.PaginationQuery(offset=0, limit=10)
    statement = domain.find_candidates_statement(query)
    rows, count = await models.User.execute_list_statement(
        statement, ordering, pagination
    )
    domain_users = [
        schemas.UserWithDomainRole.from_domain_user(*row[::-1]) for row in rows
    ]
    return StandardListResponse(domain_users, count)


@router.get("/{domain}/roles", permissions=[Permission.DomainGeneral.view])
async def list_domain_roles(
    domain: models.Domain = Depends(parse_domain_from_auth),
    ordering: schemas.OrderingQuery = Depends(parse_ordering_query()),
) -> StandardListResponse[schemas.DomainRole]:
    statement = domain.find_domain_roles_statement()
    domain_roles, count = await models.DomainRole.execute_list_statement(
        statement, ordering
    )
    return StandardListResponse(domain_roles, count)


@router.post("/{domain}/roles", permissions=[Permission.DomainGeneral.edit])
async def create_domain_role(
    domain_role_create: schemas.DomainRoleCreate,
    domain: models.Domain = Depends(parse_domain_from_auth),
) -> StandardResponse[schemas.DomainRole]:
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
    logger.info(f"create domain role: {domain_role}")
    await domain_role.save_model()
    return StandardResponse(domain_role)


@router.get("/{domain}/roles/{role}", permissions=[Permission.DomainGeneral.view])
async def get_domain_role(
    domain_role: models.DomainRole = Depends(parse_domain_role),
) -> StandardResponse[schemas.DomainRoleDetail]:
    if domain_role is None:
        raise BizError(ErrorCode.DomainRoleNotFoundError)
    return StandardResponse(domain_role)


@router.delete("/{domain}/roles/{role}", permissions=[Permission.DomainGeneral.edit])
async def delete_domain_role(
    domain_role: models.DomainRole = Depends(parse_domain_role),
    domain: models.Domain = Depends(parse_domain_from_auth),
) -> StandardResponse[Empty]:
    if domain_role.role in READONLY_ROLES:
        raise BizError(ErrorCode.DomainRoleReadOnlyError)

    count = await models.DomainUser.count_domain_user(
        domain_id=domain.id, role=domain_role.role
    )
    if count > 0:
        raise BizError(ErrorCode.DomainRoleUsedError)

    logger.info(f"delete domain role: {domain_role}")
    await domain_role.delete_model()
    return StandardResponse()


@router.patch("/{domain}/roles/{role}", permissions=[Permission.DomainGeneral.edit])
async def update_domain_role(
    domain_role_edit: schemas.DomainRoleEdit = Depends(
        schemas.DomainRoleEdit.edit_dependency
    ),
    domain_role: models.DomainRole = Depends(parse_domain_role),
    # domain: models.Domain = Depends(parse_domain_from_auth),
    # session: AsyncSession = Depends(db_session_dependency),
) -> StandardResponse[schemas.DomainRole]:
    # if domain_role_edit.role:
    #     if (
    #         domain_role.role in READONLY_ROLES
    #         or domain_role_edit.role in READONLY_ROLES
    #     ):
    #         raise BizError(ErrorCode.DomainRoleReadOnlyError)
    #     if await models.DomainRole.get_or_none(
    #         domain_id=domain.id, role=domain_role_edit.role
    #     ):
    #         raise BizError(ErrorCode.DomainRoleNotUniqueError)
    #
    #     domain_users = await models.DomainUser.get_many(
    #         domain_id=domain.id, role=domain_role.role
    #     )
    #     for domain_user in domain_users:
    #         domain_user.role = domain_role_edit.role
    #         logger.info(f"update domain user: {domain_user}")
    #         session.sync_session.add(domain_user)

    domain_role.update_from_dict(domain_role_edit.dict())
    logger.info(f"update domain role: {domain_role}")
    await domain_role.save_model()
    return StandardResponse(domain_role)


@router.get("/{domain}/invitations", permissions=[Permission.DomainGeneral.edit])
async def list_domain_invitations(
    domain: models.Domain = Depends(parse_domain_from_auth),
    ordering: schemas.OrderingQuery = Depends(parse_ordering_query()),
    pagination: schemas.PaginationQuery = Depends(parse_pagination_query),
) -> StandardListResponse[schemas.DomainInvitation]:
    statement = domain.find_domain_invitations_statement()
    invitations, count = await models.DomainInvitation.execute_list_statement(
        statement, ordering, pagination
    )
    return StandardListResponse(invitations, count)


@router.post("/{domain}/invitations", permissions=[Permission.DomainGeneral.edit])
async def create_domain_invitation(
    invitation_create: schemas.DomainInvitationCreate,
    domain: models.Domain = Depends(parse_domain_from_auth),
) -> StandardResponse[schemas.DomainInvitation]:
    if await models.DomainInvitation.get_or_none(
        domain_id=domain.id, code=invitation_create.code
    ):
        raise BizError(
            ErrorCode.DomainInvitationBadRequestError,
            "code is already used",
        )
    invitation = models.DomainInvitation(
        **invitation_create.dict(),
        domain_id=domain.id,
    )
    logger.info(f"create domain invitation: {invitation}")
    await invitation.save_model()
    return StandardResponse(invitation)


@router.get(
    "/{domain}/invitations/{invitation}", permissions=[Permission.DomainGeneral.edit]
)
async def get_domain_invitation(
    invitation: models.DomainInvitation = Depends(parse_domain_invitation),
) -> StandardResponse[schemas.DomainInvitation]:
    return StandardResponse(invitation)


@router.delete(
    "/{domain}/invitations/{invitation}", permissions=[Permission.DomainGeneral.edit]
)
async def delete_domain_invitation(
    invitation: models.DomainInvitation = Depends(parse_domain_invitation),
) -> StandardResponse[Empty]:
    logger.info(f"delete domain invitation: {invitation}")
    await invitation.delete_model()
    return StandardResponse()


@router.patch(
    "/{domain}/invitations/{invitation}", permissions=[Permission.DomainGeneral.edit]
)
async def update_domain_invitation(
    invitation_edit: schemas.DomainInvitationEdit = Depends(
        schemas.DomainInvitationEdit.edit_dependency
    ),
    invitation: models.DomainInvitation = Depends(parse_domain_invitation),
) -> StandardResponse[schemas.DomainInvitation]:
    invitation.update_from_dict(invitation_edit.dict())
    logger.info(f"update domain invitation: {invitation}")
    await invitation.save_model()
    return StandardResponse(invitation)


@router.post("/{domain}/join", permissions=[])
# @camelcase_parameters
async def join_domain_by_invitation(
    invitation_code: str = Query(...),
    domain: models.Domain = Depends(parse_domain_without_validation),
    user: models.User = Depends(parse_user_from_auth),
) -> StandardResponse[schemas.UserWithDomainRole]:
    if domain is None:
        raise BizError(ErrorCode.DomainInvitationBadRequestError)
    # validate the invitation
    invitation_model = await models.DomainInvitation.get_or_none(
        domain_id=domain.id, code=invitation_code
    )
    if invitation_model is None:
        raise BizError(ErrorCode.DomainInvitationBadRequestError)
    if (
        invitation_model.expire_at is not None
        and datetime.now(tz=timezone.utc) > invitation_model.expire_at
    ):
        raise BizError(ErrorCode.DomainInvitationExpiredError)
    # add member
    domain_user = await models.DomainUser.add_domain_user(
        domain_id=domain.id, user_id=user.id, role=invitation_model.role
    )
    logger.info(f"create domain user: {domain_user}")
    await domain_user.save_model()
    return StandardResponse(
        schemas.UserWithDomainRole.from_domain_user(domain_user, user)
    )
