from fastapi import Depends

from joj.horse import models, schemas
from joj.horse.schemas import StandardResponse
from joj.horse.schemas.domain_user import ListDomainMembers
from joj.horse.schemas.problem import ListProblems
from joj.horse.utils.auth import Authentication
from joj.horse.utils.db import generate_join_pipeline
from joj.horse.utils.parser import parse_uid
from joj.horse.utils.router import MyRouter

router = MyRouter()
router_name = "users"
router_tag = "user"
router_prefix = "/api/v1"


@router.get("/{uid}")
async def get_user(
    user: models.User = Depends(parse_uid), auth: Authentication = Depends()
) -> StandardResponse[schemas.UserBase]:
    return StandardResponse(schemas.UserBase.from_orm(user))


@router.get("/{uid}/domains")
async def get_user_domains(
    user: models.User = Depends(parse_uid),
) -> StandardResponse[ListDomainMembers]:
    pipeline = generate_join_pipeline(field="domain", condition={"user": user.id})
    return StandardResponse(
        ListDomainMembers(
            results=[
                schemas.DomainUser.from_orm(
                    models.DomainUser.build_from_mongo(domain_user), unfetch_all=False
                )
                async for domain_user in models.DomainUser.aggregate(pipeline)
            ]
        )
    )


@router.get("/{uid}/problems")
async def get_user_problems(
    user: models.User = Depends(parse_uid),
) -> StandardResponse[ListProblems]:
    return StandardResponse(
        ListProblems(
            results=[
                schemas.Problem.from_orm(problem)
                async for problem in models.Problem.find({"owner": user.id})
            ]
        )
    )
