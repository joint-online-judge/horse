from fastapi_utils.cbv import cbv
from typing import Optional
from fastapi_utils.inferring_router import InferringRouter
from fastapi import Depends

from joj.horse.utils.auth import Authentication
from joj.horse.models.permission import ScopeType, PermissionType

router = InferringRouter()
router_name = "domain"
router_prefix = "/api/v1"


@router.get("/list")
async def list_user_domains(auth: Authentication = Depends(Authentication)):
    """
    List all domains in which {user} has a role.
    Use current login user if {user} is not specified.
    """
    auth.ensure(ScopeType.GENERAL, PermissionType.UNKNOWN)

    print("self")
