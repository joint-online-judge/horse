from fastapi_utils.cbv import cbv
from typing import Optional
from fastapi_utils.inferring_router import InferringRouter
from joj.horse.utils.fastapi import Request, Pagination, Depends

router = InferringRouter()
router_name = "domain"
router_prefix = "/api/v1"


@router.get("/list")
async def list_user_domains(request: Request, user: str = None, pagination=Depends(Pagination)):
    """
    List all domains in which {user} has a role.
    Use current login user if {user} is not specified.
    """
    print("self")
