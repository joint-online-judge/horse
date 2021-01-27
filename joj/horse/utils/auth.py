from datetime import datetime, timedelta
from typing import Optional

import jose.jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from joj.horse.config import settings
from joj.horse.models.domain_role import DomainRole
from joj.horse.models.domain_user import DomainUser
from joj.horse.models.permission import DEFAULT_DOMAIN_PERMISSION, DEFAULT_SITE_PERMISSION, DefaultRole, \
    DomainPermission, PermissionType, ScopeType, SitePermission
from joj.horse.models.user import User, get_by_uname

jwt_scheme = HTTPBearer(bearerFormat='JWT', auto_error=False)


class JWTToken(BaseModel):
    sub: str
    exp: int
    name: str
    scope: str
    type: str


def generate_jwt(user: User, type: str = ''):
    exp = datetime.utcnow() + timedelta(seconds=settings.jwt_expire_seconds)
    token = JWTToken(
        sub=str(user.id),
        exp=int(exp.timestamp()),
        name=user.uname_lower,
        scope=user.scope,
        type=type,
    )
    encoded_jwt = jose.jwt.encode(token.dict(), settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded_jwt


# noinspection PyBroadException
def decode_jwt(jwt: Optional[HTTPAuthorizationCredentials] = Depends(jwt_scheme)) -> Optional[JWTToken]:
    try:
        payload = jose.jwt.decode(jwt.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return JWTToken(**payload)
    except Exception:
        return None


# noinspection PyBroadException
async def get_current_user(jwt_decoded=Depends(decode_jwt)) -> Optional[User]:
    try:
        user = await get_by_uname(scope=jwt_decoded.scope, uname=jwt_decoded.name)
        return user
    except Exception:
        return None


def get_site_role(user: Optional[User] = Depends(get_current_user)):
    if user:
        return user.role
    # the default site role is guest
    return DefaultRole.GUEST


def get_site_permission(site_role: str = Depends(get_site_role)):
    if site_role in DEFAULT_SITE_PERMISSION:
        return DEFAULT_SITE_PERMISSION[site_role]
    else:
        return DEFAULT_SITE_PERMISSION[DefaultRole.GUEST]


async def get_domain_role(
        user: Optional[User] = Depends(get_current_user),
        domain: Optional[str] = None,
):
    if user and domain:
        domain_user = await DomainUser.find_one({'domain': domain, 'user': user.id})
        if domain_user:
            return domain_user.role
    # the default site role is guest
    return DefaultRole.GUEST


async def get_domain_permission(
        domain: Optional[str] = None,
        domain_role: str = Depends(get_domain_role),
):
    if domain_role == DefaultRole.ROOT:
        return DEFAULT_DOMAIN_PERMISSION[DefaultRole.ROOT]
    if domain:
        _domain_role = await DomainRole.find_one({'domain': domain, 'role': domain_role})
    else:
        _domain_role = None
    if _domain_role:
        return _domain_role.permission
    elif domain_role in DEFAULT_DOMAIN_PERMISSION:
        return DEFAULT_DOMAIN_PERMISSION[domain_role]
    else:
        return DEFAULT_DOMAIN_PERMISSION[DefaultRole.GUEST]


class Authentication:
    def __init__(self,
                 jwt_decoded: Optional[JWTToken] = Depends(decode_jwt),
                 user: Optional[User] = Depends(get_current_user),
                 domain: Optional[str] = None,
                 site_role: str = Depends(get_site_role),
                 site_permission: Optional[SitePermission] = Depends(get_site_permission),
                 domain_role: str = Depends(get_domain_role),
                 domain_permission: Optional[DomainPermission] = Depends(get_domain_permission)):
        self.jwt = jwt_decoded
        self.user = user
        self.domain = domain
        self.site_role = site_role
        self.site_permission = site_permission.dict()
        self.domain_role = domain_role
        self.domain_permission = domain_permission.dict()

    def check(self, scope: ScopeType, permission: PermissionType) -> bool:
        def _check(permissions: Optional[dict]):
            print(permissions)
            if permissions is None:
                return False
            return permissions.get(permission, False)

        # grant site root with all permissions
        if self.site_role == DefaultRole.ROOT:
            return True
        # grant domain root with domain permissions
        if self.domain_role == DefaultRole.ROOT and scope in DEFAULT_DOMAIN_PERMISSION[DefaultRole.ROOT]:
            return True
        # grant permission if site permission found
        if self.site_permission and _check(self.site_permission.get(scope, None)):
            return True
        # grant permission if domain permission found
        if self.domain_permission and _check(self.domain_permission.get(scope, None)):
            return True
        # permission denied if every check failed
        return False

    def ensure(self, scope: ScopeType, permission: PermissionType) -> None:
        if not self.check(scope, permission):
            raise HTTPException(status_code=403, detail="%s %s Permission Denied." % (scope, permission))

    def ensure_or(self, *args) -> None:
        if not args:
            return
        scope, permission = (ScopeType.UNKNOWN, PermissionType.UNKNOWN)
        for arg in args:
            try:
                scope, permission = arg
                if self.check(scope, permission):
                    return
            except:
                pass
        raise HTTPException(status_code=403, detail="%s %s Permission Denied." % (scope, permission))

    def ensure_and(self, *args) -> None:
        for arg in args:
            self.ensure(*arg)
