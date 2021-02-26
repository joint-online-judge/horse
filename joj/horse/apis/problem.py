import aiohttp
import jwt
from typing import Optional, List
from fastapi import Cookie, Depends, HTTPException, Query, Request, status
from fastapi_jwt_auth import AuthJWT
from fastapi_utils.inferring_router import InferringRouter
from starlette.responses import JSONResponse, RedirectResponse
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.schemas.misc import RedirectModel
from joj.horse.utils import errors
from joj.horse.utils.auth import Authentication, auth_jwt_encode
from joj.horse.utils.db import instance

router = InferringRouter()
router_name = "problem"
router_prefix = "/api/v1"


async def parse_pid(pid: str, auth: Authentication = Depends()) -> models.User:
    problem = await models.Problem.find_by_id(pid)
    if problem:
        return problem
    raise errors.ProblemNotFoundError(pid)


@router.post("/create", response_model=schemas.Problem)
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
    """
    Create a new problem
    """
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


@router.get("/{pid}", response_model=schemas.Problem)
async def get_problem(problem: models.Problem = Depends(parse_pid)) -> schemas.Problem:
    return schemas.Problem.from_orm(problem)
