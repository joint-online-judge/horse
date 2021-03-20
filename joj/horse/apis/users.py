from typing import List

from fastapi import APIRouter, Depends

from joj.horse import models, schemas
from joj.horse.utils.auth import Authentication
from joj.horse.utils.db import generate_join_pipeline
from joj.horse.utils.parser import parse_uid

router = APIRouter()
router_name = "users"
router_tag = "user"
router_prefix = "/api/v1"


@router.get("/{uid}", response_model=schemas.UserBase)
async def get_user(
    user: models.User = Depends(parse_uid), auth: Authentication = Depends()
) -> schemas.UserBase:
    return schemas.UserBase.from_orm(user)


@router.get("/{uid}/domains", response_model=List[schemas.DomainUser])
async def get_user_domains(
    user: models.User = Depends(parse_uid),
) -> List[schemas.DomainUser]:
    pipeline = generate_join_pipeline(field="domain", condition={"user": user.id})
    return [
        schemas.DomainUser.from_orm(
            models.DomainUser.build_from_mongo(domain_user), unfetch_all=False
        )
        async for domain_user in models.DomainUser.aggregate(pipeline)
    ]


@router.get("/{uid}/problems", response_model=List[schemas.Problem])
async def get_user_problems(
    user: models.User = Depends(parse_uid),
) -> List[schemas.Problem]:
    return [
        schemas.Problem.from_orm(problem)
        async for problem in models.Problem.find({"owner": user.id})
    ]
