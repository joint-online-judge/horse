from fastapi import Depends

from joj.horse.schemas.misc import JWT, Version
from joj.horse.utils.auth import Authentication, jwt_token_encode
from joj.horse.utils.errors import UnauthorizedError
from joj.horse.utils.router import MyRouter
from joj.horse.utils.version import get_git_version, get_version

router = MyRouter()
router_name = ""
router_tag = "miscellaneous"
router_prefix = "/api/v1"


@router.get("/version")
async def version() -> Version:
    return Version(version=get_version(), git=get_git_version())


@router.get("/jwt")
async def jwt(auth: Authentication = Depends()) -> JWT:
    if auth.jwt:
        return JWT(jwt=jwt_token_encode(auth.jwt))
    raise UnauthorizedError(message="JWT not found")


@router.get("/test/sentry")
async def test_sentry() -> None:
    assert False
