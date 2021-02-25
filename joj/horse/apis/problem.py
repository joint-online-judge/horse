from typing import List, Optional

from fastapi import Depends, Query
from fastapi_utils.inferring_router import InferringRouter
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.utils import errors
from joj.horse.utils.auth import Authentication
from joj.horse.utils.db import instance
from joj.horse.utils.parser import parse_pid, parse_uid

router = InferringRouter()
router_name = "problems"
router_tag = "problem"
router_prefix = "/api/v1"


@router.get("", response_model=List[schemas.Problem])
async def list_problems(auth: Authentication = Depends(Authentication)):
    return [
        schemas.Problem.from_orm(problem)
        async for problem in models.Problem.find({"owner": auth.user.id})
    ]


@router.post("", response_model=schemas.Problem)
async def create_problem(
    domain: str = Query(..., description="url or the id of the domain"),
    title: str = Query(..., description="title of the problem"),
    content: Optional[str] = Query("", description="content of the problem"),
    hidden: Optional[bool] = Query(False, description="whether the problem is hidden"),
    languages: Optional[List[str]] = Query(
        [], description="acceptable language of the problem"
    ),
    auth: Authentication = Depends(),
) -> schemas.Problem:
    if auth.user is None:
        raise errors.InvalidAuthenticationError()

    # use transaction for multiple operations
    try:
        async with instance.session() as session:
            async with session.start_transaction():
                domain = await models.Domain.find_by_url_or_id(domain)
                problem = schemas.Problem(
                    title=title,
                    content=content,
                    hidden=hidden,
                    languages=languages,
                    domain=domain.id,
                    owner=auth.user.id,
                )
                problem = models.Problem(**problem.to_model())
                await problem.commit()
                logger.info("problem created: %s", problem)

    except Exception as e:
        logger.error("problem creation failed: %s", "problem")
        raise e

    return schemas.Problem.from_orm(problem)


@router.get("/{problem}", response_model=schemas.Problem)
async def get_problem(problem: models.Problem = Depends(parse_pid)) -> schemas.Problem:
    return schemas.Problem.from_orm(problem)


@router.delete("/{problem}", status_code=204)
async def delete_problem(problem: models.Problem = Depends(parse_pid)):
    await problem.delete()
