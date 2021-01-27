from fastapi import APIRouter

from joj.horse.models.misc import Version
from joj.horse.utils.version import get_git_version, get_version

router = APIRouter()
router_name = "misc"
router_prefix = "/api/v1"


@router.get("/version", response_model=Version)
async def version():
    return Version(version=get_version(), git=get_git_version())
