from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from pydantic import BaseModel

from joj.horse import app
from joj.horse.config import settings
from joj.horse.models.domain import Domain
from joj.horse.models.domain_role import DomainRole
from joj.horse.models.domain_user import DomainUser
from joj.horse.models.permission import (
    DEFAULT_DOMAIN_PERMISSION,
    DEFAULT_SITE_PERMISSION,
    DefaultRole,
    DomainPermission,
    PermissionType,
    ScopeType,
    SitePermission,
)
from joj.horse.models.user import User

jwt_scheme = HTTPBearer(bearerFormat="JWT", auto_error=False)


class JWTToken(BaseModel):
    # registered claims
    sub: str
    iat: int
    nbf: int
    jti: str
    exp: int
    # fastapi_jwt_auth claims
    type: str
    fresh: bool
    csrf: Optional[str] = None
    # user claims
    name: str
    scope: str
    channel: str


class Settings(BaseModel):
    authjwt_secret_key: str
    authjwt_algorithm: str
    authjwt_access_token_expires: int
    authjwt_cookie_max_age: int
    authjwt_access_cookie_key: str = "jwt"
    authjwt_access_csrf_cookie_key: str = "csrf"
    # Configure application to store and get JWT from cookies
    authjwt_token_location: set = {"headers", "cookies"}
    # Only allow JWT cookies to be sent over https
    authjwt_cookie_secure: bool = False
    # Enable csrf double submit protection. default is True
    authjwt_cookie_csrf_protect: bool = True


@AuthJWT.load_config
def get_config():
    return Settings(
        authjwt_secret_key=settings.jwt_secret,
        authjwt_algorithm=settings.jwt_algorithm,
        authjwt_access_token_expires=settings.jwt_expire_seconds,
        authjwt_cookie_max_age=settings.jwt_expire_seconds,
        authjwt_cookie_secure=not settings.debug,
        authjwt_cookie_csrf_protect=not settings.debug,
    )


@app.exception_handler(AuthJWTException)
def authjwt_exception_handler(request: Request, exc: AuthJWTException):
    # noinspection PyUnresolvedReferences
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


def jwt_token_encode(token: JWTToken):
    encoded_jwt = jwt.encode(
        token.dict(), settings.jwt_secret, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def auth_jwt_decode(
    auth_jwt: AuthJWT = Depends(),
    scheme: HTTPAuthorizationCredentials = Depends(jwt_scheme)
    # scheme is only used for authorization in swagger UI
) -> Optional[JWTToken]:
    auth_jwt.jwt_optional()
    payload = auth_jwt.get_raw_jwt()
    # print(payload)
    if payload:
        try:
            return JWTToken(**payload)
        except:
            raise HTTPException(status_code=401, detail="JWT Format Error")
    return None


def auth_jwt_encode(auth_jwt: AuthJWT, user: User, channel: str = "") -> str:
    user_claims = {
        "name": user.uname_lower,
        "scope": user.scope,
        "channel": channel,
    }
    jwt = auth_jwt.create_access_token(subject=str(user.id), user_claims=user_claims)
    # print(jwt)
    return jwt


# noinspection PyBroadException
async def get_current_user(jwt_decoded=Depends(auth_jwt_decode)) -> Optional[User]:
    try:
        user = await User.find_by_uname(scope=jwt_decoded.scope, uname=jwt_decoded.name)
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
    user: Optional[User] = None,
    domain: Optional[Domain] = None,
) -> str:
    if user and domain:
        domain_user = await DomainUser.find_one({"domain": domain.id, "user": user.id})
        if domain_user:
            return domain_user.role
    # the default site role is guest
    return DefaultRole.GUEST


async def get_domain_permission(
    domain: Optional[Domain] = None,
    domain_role: str = DefaultRole.GUEST,
) -> DomainPermission:
    if domain_role == DefaultRole.ROOT:
        return DEFAULT_DOMAIN_PERMISSION[DefaultRole.ROOT]
    if domain:
        _domain_role = await DomainRole.find_one(
            {"domain": domain.id, "role": domain_role}
        )
    else:
        _domain_role = None
    if _domain_role:
        return _domain_role.permission
    elif domain_role in DEFAULT_DOMAIN_PERMISSION:
        return DEFAULT_DOMAIN_PERMISSION[domain_role]
    else:
        return DEFAULT_DOMAIN_PERMISSION[DefaultRole.GUEST]


class Authentication:
    def __init__(
        self,
        jwt_decoded: Optional[JWTToken] = Depends(auth_jwt_decode),
        user: Optional[User] = Depends(get_current_user),
        site_role: str = Depends(get_site_role),
        site_permission: Optional[SitePermission] = Depends(get_site_permission),
    ):
        self.jwt: Optional[JWTToken] = jwt_decoded
        self.user: Optional[User] = user
        self.domain: Optional[Domain] = None
        self.site_role = site_role
        self.site_permission = site_permission.dump()
        self.domain_role = DefaultRole.GUEST
        self.domain_permission = DEFAULT_DOMAIN_PERMISSION[DefaultRole.GUEST].dump()

    async def init_domain(self, domain: str):
        self.domain = await Domain.find_by_url_or_id(domain)
        if self.domain:
            self.domain_role = await get_domain_role(self.user, self.domain)
            self.domain_permission = (
                await get_domain_permission(self.domain, self.domain_role)
            ).dump()
        # print(self.domain, self.domain_role, self.domain_permission)

    def check(self, scope: ScopeType, permission: PermissionType) -> bool:
        def _check(permissions: Optional[dict]):
            # print(permissions)
            if permissions is None:
                return False
            return permissions.get(permission, False)

        # grant site root with all permissions
        if self.site_role == DefaultRole.ROOT:
            return True
        # grant domain root with domain permissions
        if (
            self.domain_role == DefaultRole.ROOT
            and scope in DEFAULT_DOMAIN_PERMISSION[DefaultRole.ROOT]
        ):
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
            raise HTTPException(
                status_code=403, detail="%s %s Permission Denied." % (scope, permission)
            )

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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="%s %s Permission Denied." % (scope, permission),
        )

    def ensure_and(self, *args) -> None:
        for arg in args:
            self.ensure(*arg)
