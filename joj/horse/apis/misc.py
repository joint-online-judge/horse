from joj.horse.utils.fastapi import APIRouter, Request, HTTPException
from joj.horse.utils.version import get_version, get_git_version

from joj.horse.models.misc import Version

router = APIRouter()
router_name = "misc"
router_prefix = "/api/v1"


@router.get("/version", response_model=Version)
async def version():
    return Version(version=get_version(), git=get_git_version())
