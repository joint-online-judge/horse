from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from joj.horse import models, schemas
from joj.horse.models.permission import DefaultRole
from joj.horse.schemas.base import StandardResponse
from joj.horse.schemas.misc import Version
from joj.horse.utils.auth import JWTAccessToken, auth_jwt_decode_access_token
from joj.horse.utils.db import db_session_dependency
from joj.horse.utils.errors import BizError, ErrorCode
from joj.horse.utils.parser import parse_user_from_auth
from joj.horse.utils.router import MyRouter
from joj.horse.utils.version import get_git_version, get_version

router = MyRouter()
router_name = ""
router_tag = "miscellaneous"
router_prefix = "/api/v1"


@router.get("/version")
async def version() -> Version:
    return Version(version=get_version(), git=get_git_version())


# @router.get("/jwt")
# async def jwt(auth_jwt: AuthJWT = Depends(), auth: Authentication = Depends()) -> JWT:
#     if auth.jwt:
#         access_token, refresh_token =
#         return JWT(jwt=auth_jwt_encode_user(auth_jwt, auth.user, auth.oauth_profile))
#     raise UnauthorizedError(message="JWT not found")


@router.get("/jwt_decoded")
async def jwt_decoded(
    jwt_access_token: JWTAccessToken = Depends(auth_jwt_decode_access_token),
) -> StandardResponse[JWTAccessToken]:
    return StandardResponse(jwt_access_token)


@router.get("/test/report")
async def test_error_report() -> None:
    assert False


@router.post("/set_root_user")
async def set_root_user(
    user: models.User = Depends(parse_user_from_auth),
    session: AsyncSession = Depends(db_session_dependency),
) -> StandardResponse[schemas.User]:
    root_user = await models.User.get_or_none(role=DefaultRole.ROOT)
    if root_user is not None:
        raise BizError(ErrorCode.Error)

    current_user = await models.User.get_or_none(id=user.id)
    current_user.role = DefaultRole.ROOT
    session.sync_session.add(current_user)
    await session.commit()
    await session.refresh(current_user)
    return StandardResponse(current_user)
