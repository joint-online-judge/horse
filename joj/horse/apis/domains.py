from http import HTTPStatus
from typing import List

from bson import ObjectId
from fastapi import APIRouter, Depends, Query, Response
from marshmallow.exceptions import ValidationError
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.models.permission import DefaultRole, PermissionType, ScopeType
from joj.horse.schemas.user import UserBase
from joj.horse.utils.auth import Authentication, DomainAuthentication
from joj.horse.utils.db import instance
from joj.horse.utils.errors import InvalidAuthenticationError, InvalidDomainURLError
from joj.horse.utils.parser import parse_domain, parse_uid

router = APIRouter()
router_name = "domains"
router_tag = "domain"
router_prefix = "/api/v1"


@router.get("", response_model=List[schemas.Domain])
async def list_domains(
    auth: Authentication = Depends(Authentication),
) -> List[schemas.Domain]:
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
async def get_domain(auth: DomainAuthentication = Depends()) -> schemas.Domain:
    await auth.domain.owner.fetch()
    return schemas.Domain.from_orm(auth.domain)


@router.delete("/{domain}", status_code=HTTPStatus.NO_CONTENT)
async def delete_domain(
    domain: models.Domain = Depends(parse_domain), auth: Authentication = Depends()
) -> None:
    # TODO: finish this part
    await domain.delete()


@router.patch("/{domain}", response_model=schemas.Domain)
async def update_domain(
    edit_doamin: schemas.EditDomain,
    domain: models.Domain = Depends(parse_domain),
    auth: Authentication = Depends(Authentication),
) -> schemas.Domain:
    domain.update_from_schema(edit_doamin)
    await domain.commit()
    return schemas.Domain.from_orm(domain)


@router.get("/{domain}/members", response_model=List[schemas.UserBase])
async def list_members_in_domain(
    domain: models.Domain = Depends(parse_domain),
    auth: Authentication = Depends(Authentication),
) -> List[schemas.UserBase]:
    return [
        await domain_user.user.fetch()
        async for domain_user in models.DomainUser.find({"domain": domain.id})
    ]


@router.post("/{domain}/members/{uid}", status_code=HTTPStatus.NO_CONTENT)
async def add_member_to_domain(
    domain: models.Domain = Depends(parse_domain),
    user: models.User = Depends(parse_uid),
    auth: Authentication = Depends(Authentication),
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
    auth: Authentication = Depends(Authentication),
) -> None:
    domain_user = await models.DomainUser.find_one(
        {"domain": domain.id, "user": user.id}
    )
    if domain_user:
        await domain_user.delete()


@router.get("/{domain}/labels", response_model=List[str])
async def list_labels_in_domain(
    domain: models.Domain = Depends(parse_domain),
    auth: Authentication = Depends(Authentication),
) -> List[str]:
    # TODO: aggregate
    return [
        label
        async for problem_set in models.ProblemSet.find({"domain": domain.id})
        for label in schemas.ProblemSet.from_orm(problem_set).labels
    ]
