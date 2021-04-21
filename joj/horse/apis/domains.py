from http import HTTPStatus
from typing import List

from bson import ObjectId
from fastapi import APIRouter, Body, Depends, Query, Response
from marshmallow.exceptions import ValidationError
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.models.permission import DefaultRole, PermissionType, ScopeType
from joj.horse.schemas.user import UserBase
from joj.horse.utils.auth import Authentication, DomainAuthentication, ensure_permission
from joj.horse.utils.db import generate_join_pipeline, instance
from joj.horse.utils.errors import (
    APINotImplementedError,
    InvalidAuthenticationError,
    InvalidDomainURLError,
)
from joj.horse.utils.parser import parse_domain, parse_domain_from_auth, parse_uid

router = APIRouter()
router_name = "domains"
router_tag = "domain"
router_prefix = "/api/v1"


@router.get("", response_model=List[schemas.Domain])
async def list_domains(auth: Authentication = Depends(),) -> List[schemas.Domain]:
    """
    List all domains in which {user} has a role.
    Use current login user if {user} is not specified.
    """
    # TODO: finish this part
    # auth.ensure(ScopeType.GENERAL, PermissionType.UNKNOWN)
    # print("self")
    return [
        schemas.Domain.from_orm(domain)
        async for domain in models.Domain.find({"owner": auth.user.id})
    ]


@router.post(
    "",
    response_model=schemas.Domain,
    dependencies=[
        Depends(ensure_permission(ScopeType.SITE_DOMAIN, PermissionType.CREATE))
    ],
)
async def create_domain(
    domain: schemas.DomainCreate, auth: Authentication = Depends()
) -> schemas.Domain:
    # we can not use ObjectId as the url
    if ObjectId.is_valid(domain.url):
        raise InvalidDomainURLError(domain.url)
    if auth.user is None:
        raise InvalidAuthenticationError()

    # use transaction for multiple operations
    try:
        async with instance.session() as session:
            async with session.start_transaction():
                domain = schemas.Domain(**domain.dict(), owner=auth.user.id)
                domain = models.Domain(**domain.to_model())
                await domain.commit()
                logger.info("domain created: %s", domain)
                domain_user = schemas.DomainUser(
                    domain=domain.id, user=auth.user.id, role=DefaultRole.ROOT
                )
                domain_user = models.DomainUser(**domain_user.to_model())
                await domain_user.commit()
                logger.info("domain user created: %s", domain_user)
                # TODO: create domain roles here
    except ValidationError:
        raise InvalidDomainURLError(domain.url)  # non-unique domain url
    except Exception as e:
        logger.error("domain creation failed: %s", domain.url)
        raise e

    return schemas.Domain.from_orm(domain)


@router.get(
    "/{domain}",
    response_model=schemas.Domain,
    dependencies=[
        # Depends(ensure_permission(ScopeType.SITE_USER, PermissionType.VIEW_HIDDEN)),
        Depends(ensure_permission(ScopeType.DOMAIN_GENERAL, PermissionType.VIEW))
    ],
)
async def get_domain(
    domain: models.Domain = Depends(parse_domain_from_auth),
) -> schemas.Domain:
    await domain.owner.fetch()
    return schemas.Domain.from_orm(domain, unfetch_all=False)


@router.delete(
    "/{domain}",
    status_code=HTTPStatus.NO_CONTENT,
    response_class=Response,
    dependencies=[
        Depends(ensure_permission(ScopeType.SITE_DOMAIN, PermissionType.DELETE))
    ],
    deprecated=True,
)
async def delete_domain(
    domain: models.Domain = Depends(parse_domain_from_auth),
) -> None:
    # TODO: finish this part
    # tc-imba: delete domain have many side effects, and is not urgent,
    #          marked it deprecated and implement it later
    raise APINotImplementedError()
    # await domain.delete()


@router.patch(
    "/{domain}",
    response_model=schemas.Domain,
    dependencies=[
        Depends(ensure_permission(ScopeType.DOMAIN_GENERAL, PermissionType.EDIT))
    ],
)
async def update_domain(
    domain_edit: schemas.DomainEdit,
    domain: models.Domain = Depends(parse_domain_from_auth),
) -> schemas.Domain:
    domain.update_from_schema(domain_edit)
    await domain.commit()
    return schemas.Domain.from_orm(domain)


@router.get("/{domain}/members", response_model=List[schemas.DomainUser])
async def list_members_in_domain(
    domain: models.Domain = Depends(parse_domain),
    auth: DomainAuthentication = Depends(DomainAuthentication),
) -> List[schemas.DomainUser]:
    pipeline = generate_join_pipeline(field="user", condition={"domain": domain.id})
    return [
        schemas.DomainUser.from_orm(
            models.DomainUser.build_from_mongo(domain_user), unfetch_all=False
        )
        async for domain_user in models.DomainUser.aggregate(pipeline)
    ]


@router.post("/{domain}/members/{uid}", status_code=HTTPStatus.NO_CONTENT)
async def add_member_to_domain(
    domain: models.Domain = Depends(parse_domain),
    user: models.User = Depends(parse_uid),
    auth: Authentication = Depends(),
) -> None:
    domain_user = schemas.DomainUser(
        domain=domain.id, user=user.id, role=DefaultRole.USER
    )
    domain_user = models.DomainUser(**domain_user.to_model())
    await domain_user.commit()


@router.delete("/{domain}/members/{uid}", status_code=HTTPStatus.NO_CONTENT)
async def remove_member_from_domain(
    domain: models.Domain = Depends(parse_domain),
    user: models.User = Depends(parse_uid),
    auth: Authentication = Depends(),
) -> None:
    domain_user = await models.DomainUser.find_one(
        {"domain": domain.id, "user": user.id}
    )
    if domain_user:
        await domain_user.delete()


@router.get("/{domain}/labels", response_model=List[str])
async def list_labels_in_domain(
    domain: models.Domain = Depends(parse_domain), auth: Authentication = Depends()
) -> List[str]:
    # TODO: aggregate
    return [
        label
        async for problem_set in models.ProblemSet.find({"domain": domain.id})
        for label in schemas.ProblemSet.from_orm(problem_set).labels
    ]
