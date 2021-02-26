from typing import List, Union

from fastapi import Depends
from fastapi_utils.inferring_router import InferringRouter

from joj.horse import models, schemas
from joj.horse.utils.auth import Authentication
from joj.horse.utils.parser import parse_uid

router = InferringRouter()
router_name = "users"
router_tag = "user"
router_prefix = "/api/v1"


@router.get("/{uid}", response_model=Union[schemas.User, schemas.UserBase])
async def get_user(
    user: models.User = Depends(parse_uid), auth: Authentication = Depends()
) -> Union[schemas.User, schemas.UserBase]:
    if user == auth.user:
        return schemas.User.from_orm(user)
    return schemas.UserBase.from_orm(user)


@router.get("/{uid}/domains", response_model=List[schemas.DomainUser])
async def get_user_domains(user: models.User = Depends(parse_uid)):
    # TODO: this pipeline may be useful in many places, consider changing it to a function
    pipeline = [
        {"$match": {"user": user.id}},
        {
            "$lookup": {
                "from": "domains",
                "localField": "domain",
                "foreignField": "_id",
                "as": "domain",
            }
        },
        {"$addFields": {"domain": {"$arrayElemAt": ["$domain", 0]}}},
    ]
    return [
        schemas.DomainUser.from_orm(models.DomainUser.build_from_mongo(domain_user))
        async for domain_user in models.DomainUser.aggregate(pipeline)
    ]


@router.get("/{uid}/problems", response_model=List[schemas.Problem])
async def get_user_problems(user: models.User = Depends(parse_uid)):
    return [
        schemas.Problem.from_orm(problem)
        async for problem in models.Problem.find({"owner": user.id})
    ]
