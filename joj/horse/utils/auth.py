from datetime import datetime, timedelta
from typing import Optional

import jose.jwt
from bson import ObjectId
from fastapi import Depends, HTTPException
from pydantic import BaseModel

from joj.horse.config import settings
from joj.horse.models.domain_role import DomainRole
from joj.horse.models.domain_user import DomainUser
from joj.horse.models.permission import DEFAULT_DOMAIN_PERMISSION, DEFAULT_SITE_PERMISSION, DefaultRole, \
    DomainPermission, PermissionType, ScopeType, SitePermission
from joj.horse.models.user import User, get_by_uname


class JWTToken(BaseModel):
    aud: str
    iss: str
    sub: str
    exp: str
    iat: str
    name: str
    code: str
    type: str
    scope: str


async def generate_jwt(user: User, type: str = ''):
    to_encode = {
        'sub': user.id,
        'name': user.uname_lower,
        'scope': user.scope,
        'exp': datetime.utcnow() + timedelta(seconds=settings.jwt_expire_seconds),
        'type': type,
    }
    encoded_jwt = jose.jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    print(encoded_jwt)
    return encoded_jwt


# noinspection PyBroadException
async def decode_jwt(jwt: str = '') -> Optional[JWTToken]:
    try:
        payload = jose.jwt.decode(jwt, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        print(payload)
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


async def get_site_role(user: Optional[User] = Depends(get_current_user)):
    if user:
        return user.role
    # the default site role is guest
    return DefaultRole.GUEST


async def get_site_permission(site_role: str = Depends(get_site_role)):
    if site_role in DEFAULT_SITE_PERMISSION:
        return DEFAULT_SITE_PERMISSION[site_role]
    else:
        return DEFAULT_SITE_PERMISSION[DefaultRole.GUEST]


async def get_domain_role(
        user: Optional[User] = Depends(get_current_user),
        domain: Optional[ObjectId] = None,
):
    if user and domain:
        domain_user = await DomainUser.find_one({'domain': domain, 'user': user.id})
        if domain_user:
            return domain_user.role
    # the default site role is guest
    return DefaultRole.GUEST


async def get_domain_permission(
        domain: Optional[ObjectId] = None,
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
                 domain: Optional[ObjectId] = None,
                 site_role: str = Depends(get_site_role),
                 site_permission: Optional[SitePermission] = Depends(get_site_permission),
                 domain_role: str = Depends(get_domain_role),
                 domain_permission: Optional[DomainPermission] = Depends(get_domain_permission)):
        self.jwt = jwt_decoded
        self.user = user
        self.domain = domain
        self.site_role = site_role
        self.site_permission = site_permission
        self.domain_role = domain_role
        self.domain_permission = domain_permission

    # async def init(self) -> 'Authentication':
    #     if self.user:
    #         self.site_role = self.user.role
    #     if self.site_role == DefaultRole.ROOT:
    #         return self
    #     if self.site_role in DEFAULT_SITE_PERMISSION:
    #         self.site_permission = DEFAULT_SITE_PERMISSION[self.site_role]
    #     else:
    #         self.site_permission = DEFAULT_SITE_PERMISSION[DefaultRole.GUEST]
    #     if self.user and self.domain:
    #         domain_user = await DomainUser.find_one({'domain': self.domain, 'user': self.user.id})
    #         if domain_user:
    #             self.domain_role = domain_user.role
    #     if self.domain_role == DefaultRole.ROOT:
    #         return self
    #     if self.domain:
    #         domain_role = await DomainRole.find_one({'domain': self.domain, 'role': self.domain_role})
    #     else:
    #         domain_role = None
    #     if domain_role:
    #         self.domain_permission = domain_role.permission
    #     elif self.domain_role in DEFAULT_DOMAIN_PERMISSION:
    #         self.domain_permission = DEFAULT_DOMAIN_PERMISSION[self.domain_role]
    #     else:
    #         self.domain_permission = DEFAULT_DOMAIN_PERMISSION[DefaultRole.GUEST]
    #     return self

    def check(self, scope: ScopeType, permission: PermissionType) -> bool:
        def _check(permissions: Optional[BaseModel]):
            if permissions is None or permission not in permissions.__fields_set__:
                return False
            return permissions.__fields__.get(permission, False)

        # grant site root with all permissions
        if self.site_role == DefaultRole.ROOT:
            return True
        # grant domain root with domain permissions
        if self.domain_role == DefaultRole.ROOT and scope in DEFAULT_DOMAIN_PERMISSION[DefaultRole.ROOT]:
            return True
        # grant permission if site permission found
        if self.site_permission and _check(self.site_permission.__fields__.get(scope, None)):
            return True
        # grant permission if domain permission found
        if self.domain_permission and _check(self.domain_permission.__fields__.get(scope, None)):
            return True
        # permission denied if every check failed
        return False

    def ensure(self, scope: ScopeType, permission: PermissionType) -> None:
        if not self.check(scope, permission):
            raise HTTPException(status_code=403, detail="%s.%s Permission Denied." % (scope, permission))

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
        raise HTTPException(status_code=403, detail="%s.%s Permission Denied." % (scope, permission))

    def ensure_and(self, *args) -> None:
        for arg in args:
            self.ensure(*arg)
