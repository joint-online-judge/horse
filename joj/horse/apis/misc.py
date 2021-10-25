from fastapi import Depends

from joj.horse.schemas.base import StandardResponse
from joj.horse.schemas.misc import Version
from joj.horse.utils.auth import JWTAccessToken, auth_jwt_decode_access_token
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


@router.get("/test/sentry")
async def test_sentry() -> None:
    assert False
