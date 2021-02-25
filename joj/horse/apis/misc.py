from fastapi import APIRouter, Depends, HTTPException, status

from joj.horse.schemas.misc import JWT, Version
from joj.horse.utils.auth import Authentication, jwt_token_encode
from joj.horse.utils.version import get_git_version, get_version

router = APIRouter()
router_name = ""
router_tag = "miscellaneous"
router_prefix = "/api/v1"


@router.get("/version", response_model=Version)
async def version():
    return Version(version=get_version(), git=get_git_version())


@router.get("/jwt", response_model=JWT)
async def jwt(auth: Authentication = Depends()):
    if auth.jwt:
        return JWT(jwt=jwt_token_encode(auth.jwt))
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="JWT not found"
    )
