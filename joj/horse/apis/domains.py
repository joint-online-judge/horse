from http import HTTPStatus
from typing import List, Optional

from bson import ObjectId
from fastapi import Depends, Query
from fastapi_utils.inferring_router import InferringRouter
from marshmallow.exceptions import ValidationError
from starlette.responses import Response
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.apis.base import DomainPath
from joj.horse.models.permission import DefaultRole, PermissionType, ScopeType
from joj.horse.utils.auth import Authentication
from joj.horse.utils.db import instance
from joj.horse.utils.errors import (
    DomainNotFoundError,
    InvalidAuthenticationError,
    InvalidDomainURLError,
)

router = InferringRouter()
router_name = "domains"
router_tag = "domain"
router_prefix = "/api/v1"


@router.get("", response_model=List[schemas.Domain])
async def list_domains(
    auth: Authentication = Depends(Authentication), uid: Optional[str] = None
) -> List[schemas.Domain]:
    """
    List all domains in which {user} has a role.
    Use current login user if {user} is not specified.
    """
    # TODO: finish this part
    auth.ensure(ScopeType.GENERAL, PermissionType.UNKNOWN)
    print("self")
    return []


@router.post("", response_model=schemas.Domain)
async def create_domain(
    url: str = Query(..., description="(unique) url of the domain"),
    name: str = Query(..., description="displayed name of the domain"),
    bulletin: str = Query("", description="bulletin of the domain"),
    gravatar: str = Query("", description="gravatar url of the domain"),
    auth: Authentication = Depends(),
) -> schemas.Domain:
    # we can not use ObjectId as the url
    if ObjectId.is_valid(url):
        raise InvalidDomainURLError(url)
    if auth.user is None:
        raise InvalidAuthenticationError()

    # use transaction for multiple operations
    try:
        async with instance.session() as session:
            async with session.start_transaction():
                domain = schemas.Domain(
                    url=url,
                    name=name,
                    bulletin=bulletin,
                    gravatar=gravatar,
                    owner=auth.user.id,
                )
                domain = models.Domain(**domain.to_model())
                await domain.commit()
                logger.info("domain created: %s", domain)
                domain_user = schemas.DomainUser(
                    domain=domain.id, user=auth.user.id, role=DefaultRole.ROOT
                )
                domain_user = models.DomainUser(**domain_user.to_model())
                await domain_user.commit()
                logger.info("domain user created: %s", domain_user)
    except ValidationError:
        raise InvalidDomainURLError(url)  # non-unique domain url
    except Exception as e:
        logger.error("domain creation failed: %s", url)
        raise e

    return schemas.Domain.from_orm(domain)


@router.get("/{domain}", response_model=schemas.Domain)
async def get_domain(
    domain: str = DomainPath, auth: Authentication = Depends()
) -> schemas.Domain:
    await auth.init_domain(domain)
    if auth.domain:
        await auth.domain.owner.fetch()
        return schemas.Domain.from_orm(auth.domain)
    raise DomainNotFoundError(domain)


@router.delete("/{domain}", status_code=HTTPStatus.NO_CONTENT)
async def delete_domain(domain: str = DomainPath, auth: Authentication = Depends()):
    # TODO: finish this part
    # await domain.delete()
    return Response(status_code=HTTPStatus.NO_CONTENT.value)


@router.patch("/{domain}", response_model=schemas.Domain)
async def update_domain(
    edit_doamin: schemas.EditDomain, domain: str = DomainPath
) -> schemas.Domain:
    domain_model = await models.Domain.find_by_url_or_id(domain)
    if edit_doamin.gravatar is not None:
        domain_model.gravatar = edit_doamin.gravatar
    if edit_doamin.bulletin is not None:
        domain_model.bulletin = edit_doamin.bulletin
    await domain_model.commit()
    return schemas.Domain.from_orm(domain_model)
