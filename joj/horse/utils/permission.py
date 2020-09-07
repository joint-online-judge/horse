from typing import Optional
from bson import ObjectId
from pydantic import BaseModel

from joj.horse.models.permission import \
    ScopeType, PermissionType, DomainPermission, SitePermission, \
    DEFAULT_DOMAIN_PERMISSION, DEFAULT_SITE_PERMISSION, DefaultRole
from joj.horse.models.domain_user import DomainUser
from joj.horse.models.domain_role import DomainRole
from joj.horse.models.user import User
from joj.horse.utils.fastapi import HTTPException


class PermissionChecker:
    def __init__(self, user: User, domain: Optional[ObjectId]):
        self.user = user
        self.domain = domain
        # the default role is guest
        self.site_role = DefaultRole.GUEST
        self.domain_role = DefaultRole.GUEST
        self.site_permission: Optional[SitePermission] = None
        self.domain_permission: Optional[DomainPermission] = None

    async def init(self) -> 'PermissionChecker':
        if self.user and await self.user.reload():
            self.site_role = self.user.role
        if self.site_role == DefaultRole.ROOT:
            return self
        if self.site_role in DEFAULT_SITE_PERMISSION:
            self.site_permission = DEFAULT_SITE_PERMISSION[self.site_role]
        else:
            self.site_permission = DEFAULT_SITE_PERMISSION[DefaultRole.GUEST]
        if self.user and self.domain:
            domain_user = await DomainUser.find_one({'domain': self.domain, 'user': self.user.id})
            if domain_user:
                self.domain_role = domain_user.role
        if self.domain_role == DefaultRole.ROOT:
            return self
        if self.domain:
            domain_role = await DomainRole.find_one({'domain': self.domain, 'role': self.domain_role})
        else:
            domain_role = None
        if domain_role:
            self.domain_permission = domain_role.permission
        elif self.domain_role in DEFAULT_DOMAIN_PERMISSION:
            self.domain_permission = DEFAULT_DOMAIN_PERMISSION[self.domain_role]
        else:
            self.domain_permission = DEFAULT_DOMAIN_PERMISSION[DefaultRole.GUEST]
        return self

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
