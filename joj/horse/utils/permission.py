from typing import Union, Optional
from bson import ObjectId
from pydantic import BaseModel

from joj.horse.models.permission import ScopeType, PermissionType, Permission
from joj.horse.models.domain_user import DomainUser
from joj.horse.models.domain_role import DomainRole
from joj.horse.utils.session import Session
from joj.horse.utils.fastapi import HTTPException


class PermissionChecker:
    def __init__(self, session: Session, domain: ObjectId):
        self.user = session.user
        self.domain = domain
        self.permission: Optional[Permission] = None

    async def init(self):
        if self.user:
            domain_user = await DomainUser.find_one({'domain': self.domain, 'user': self.user.id})
            if domain_user:
                domain_role = await DomainRole.find_one({'domain': self.domain, 'role': domain_user.role})
                if domain_role:
                    self.permission = domain_role.permission
                    return self
        self.permission = Permission()
        return self

    def check(self, scope: ScopeType, permission: PermissionType) -> bool:
        if self.permission is None or scope.value not in self.permission.__fields_set__:
            return False
        permissions: Optional[BaseModel] = self.permission.__fields__.get(scope.value, None)
        if permissions is None or permission.value not in permissions.__fields_set__:
            return False
        return permissions.__fields__.get(permission.value, False)

    def ensure(self, scope: ScopeType, permission: PermissionType):
        if not self.check(scope, permission):
            raise HTTPException(status_code=403, detail="%s.%s Permission Denied." % (scope.value, permission.value))

    def ensure_or(self, *args):
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
        raise HTTPException(status_code=403, detail="%s.%s Permission Denied." % (scope.value, permission.value))

    def ensure_and(self, *args):
        for arg in args:
            self.ensure(*arg)
