from typing import List, Union

import aiohttp
import jwt
from fastapi import Cookie, Depends, HTTPException, Query, Request, status
from fastapi_jwt_auth import AuthJWT
from fastapi_utils.inferring_router import InferringRouter
from starlette.responses import JSONResponse, RedirectResponse
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.schemas.misc import RedirectModel
from joj.horse.utils.auth import Authentication, auth_jwt_encode
from joj.horse.utils.oauth import jaccount
from joj.horse.utils.parser import parse_uid
from joj.horse.utils.url import generate_url

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


@router.get("/{uid}/domains", response_model=List[schemas.Domain])
async def get_user_domains(user: models.User = Depends(parse_uid)):
    return [
        schemas.Domain.from_orm(domain)
        async for domain in models.Domain.find({"owner": user.id})
    ]


@router.get("/{uid}/problems", response_model=List[schemas.Problem])
async def get_user_problems(user: models.User = Depends(parse_uid)):
    return [
        schemas.Problem.from_orm(problem)
        async for problem in models.Problem.find({"owner": user.id})
    ]
