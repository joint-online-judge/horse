from typing import Optional

from bson import ObjectId
from fastapi import Depends, Query
from fastapi_utils.inferring_router import InferringRouter
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.apis.base import DomainPath
from joj.horse.models.permission import DefaultRole, PermissionType, ScopeType
from joj.horse.utils import errors
from joj.horse.utils.auth import Authentication
from joj.horse.utils.db import instance

router = InferringRouter()
router_name = "domain"
router_prefix = "/api/v1"


@router.get("/list")
async def list_user_domains(
    auth: Authentication = Depends(Authentication), uid: Optional[str] = None
):
    """
    List all domains in which {user} has a role.
    Use current login user if {user} is not specified.
    """
    auth.ensure(ScopeType.GENERAL, PermissionType.UNKNOWN)
    print("self")


@router.post("/create")
async def create_domain(
    url: str = Query(..., description="(unique) url of the domain"),
    name: str = Query(..., description="displayed name of the domain"),
    auth: Authentication = Depends(),
) -> schemas.Domain:
    # we can not use routing path or ObjectId as the url
    if url == "create" or ObjectId.is_valid(url):
        raise errors.InvalidDomainURLError(url)
    if auth.user is None:
        raise errors.InvalidAuthenticationError()

    # use transaction for multiple operations
    try:
        async with instance.session() as session:
            async with session.start_transaction():
                domain = schemas.Domain(url=url, name=name, owner=auth.user.id)
                domain = models.Domain(**domain.to_model())
                await domain.commit()
                logger.info("domain created: %s", domain)
                domain_user = schemas.DomainUser(
                    domain=domain.id, user=auth.user.id, role=DefaultRole.ROOT
                )
                domain_user = models.DomainUser(**domain_user.to_model())
                await domain_user.commit()
                logger.info("domain user created: %s", domain_user)

    except Exception as e:
        logger.error("domain creation failed: %s", url)
        raise e

    return schemas.Domain.from_orm(domain)


@router.get("/{domain}")
async def get_domain(
    domain: str = DomainPath, auth: Authentication = Depends()
) -> schemas.Domain:
    await auth.init_domain(domain)
    if auth.domain:
        await auth.domain.owner.fetch()
        return schemas.Domain.from_orm(auth.domain)
    raise errors.DomainNotFoundError(domain)
