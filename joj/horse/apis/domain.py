from typing import Optional

from fastapi import Depends
from fastapi_utils.inferring_router import InferringRouter

from joj.horse import models, schemas
from joj.horse.models.permission import PermissionType, ScopeType
from joj.horse.utils.auth import Authentication

router = InferringRouter()
router_name = "domain"
router_prefix = "/api/v1"


@router.get("/list")
async def list_user_domains(auth: Authentication = Depends(Authentication), uid: Optional[str] = None):
    """
    List all domains in which {user} has a role.
    Use current login user if {user} is not specified.
    """
    auth.ensure(ScopeType.GENERAL, PermissionType.UNKNOWN)
    print("self")


@router.post("/create")
async def create_domain(url: str, name: str, auth: Authentication = Depends()):
    domain = schemas.Domain(
        url=url,
        name=name,
        owner=auth.user.id
    )
    domain = models.Domain(**domain.dict())
    print(domain)
    await domain.commit()
