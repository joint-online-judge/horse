from fastapi import Depends

from joj.horse.schemas.auth import JWTAccessToken, auth_jwt_decode_access_token
from joj.horse.schemas.base import Empty, StandardResponse
from joj.horse.schemas.misc import Version
from joj.horse.utils.fastapi.router import APIRouter
from joj.horse.utils.version import get_git_version, get_version

router = APIRouter()
router_name = ""
router_tag = "miscellaneous"


@router.get("/version")
async def version() -> Version:
    return Version(version=get_version(), git=get_git_version())


@router.get("/jwt_decoded")
async def jwt_decoded(
    jwt_access_token: JWTAccessToken = Depends(auth_jwt_decode_access_token),
) -> StandardResponse[JWTAccessToken]:
    return StandardResponse(jwt_access_token)


@router.get("/test/report")
async def test_error_report() -> StandardResponse[Empty]:
    assert False
    return StandardResponse()  # lgtm [py/unreachable-statement]
