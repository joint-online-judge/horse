from typing import Any, Callable, Dict, List, NamedTuple, Optional, Set, Tuple, Union

import jwt
from fastapi import Depends, Path
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi_jwt_auth import AuthJWT
from typing_extensions import Literal

from joj.horse.config import settings
from joj.horse.models.domain import Domain
from joj.horse.models.domain_role import DomainRole
from joj.horse.models.domain_user import DomainUser
from joj.horse.models.user import User
from joj.horse.schemas import BaseModel
from joj.horse.schemas.permission import (
    DEFAULT_DOMAIN_PERMISSION,
    DEFAULT_SITE_PERMISSION,
    DefaultRole,
    DomainPermission,
    PermissionType,
    ScopeType,
    SitePermission,
)
from joj.horse.utils.errors import (
    BizError,
    ErrorCode,
    ForbiddenError,
    InternalServerError,
    UnauthorizedError,
)

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
    authjwt_token_location: Set[str] = {"headers", "cookies"}
    # Only allow JWT cookies to be sent over https
    authjwt_cookie_secure: bool = False
    # Enable csrf double submit protection. default is True
    authjwt_cookie_csrf_protect: bool = True


@AuthJWT.load_config
def get_config() -> Settings:
    return Settings(
        authjwt_secret_key=settings.jwt_secret,
        authjwt_algorithm=settings.jwt_algorithm,
        authjwt_access_token_expires=settings.jwt_expire_seconds,
        authjwt_cookie_max_age=settings.jwt_expire_seconds,
        authjwt_cookie_secure=not settings.debug,
        authjwt_cookie_csrf_protect=not settings.debug,
    )


def jwt_token_encode(token: JWTToken) -> bytes:
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
    if payload:
        try:
            return JWTToken(**payload)
        except Exception:
            raise UnauthorizedError(message="JWT Format Error")
    return None


def auth_jwt_encode(auth_jwt: AuthJWT, user: User, channel: str = "") -> str:
    user_claims = {"name": user.uname_lower, "scope": user.scope, "channel": channel}
    return auth_jwt.create_access_token(subject=str(user.id), user_claims=user_claims)


# noinspection PyBroadException
async def get_current_user(jwt_decoded: JWTToken = Depends(auth_jwt_decode)) -> User:
    try:
        user = await User.find_by_uname(scope=jwt_decoded.scope, uname=jwt_decoded.name)
        if user is None:
            raise Exception()
    except Exception:
        raise UnauthorizedError(message="Unauthorized")
    return user


def get_site_role(user: Optional[User] = Depends(get_current_user)) -> str:
    if user:
        return user.role
    # the default site role is guest
    return DefaultRole.GUEST


def get_site_permission(site_role: str = Depends(get_site_role)) -> SitePermission:
    if site_role in DEFAULT_SITE_PERMISSION:
        return DEFAULT_SITE_PERMISSION[DefaultRole(site_role)]
    else:
        return DEFAULT_SITE_PERMISSION[DefaultRole.GUEST]


async def get_domain(
    domain: str = Path(..., description="url or ObjectId of the domain"),
) -> Domain:
    domain_model = await Domain.find_by_url_or_id(domain)
    if domain_model is None:
        raise BizError(ErrorCode.DomainNotFoundError)
    return domain_model


async def get_domain_role(
    user: Optional[User] = Depends(get_current_user),
    domain: Domain = Depends(get_domain),
) -> str:
    if user:
        domain_user = await DomainUser.get_or_none(domain=domain.id, user=user.id)
        if domain_user:
            return domain_user.role
    # the default site role is guest
    return DefaultRole.GUEST


async def get_domain_permission(
    domain: Domain = Depends(get_domain), domain_role: str = Depends(get_domain_role)
) -> DomainPermission:
    if domain_role == DefaultRole.ROOT:
        return DEFAULT_DOMAIN_PERMISSION[DefaultRole.ROOT]
    if domain:
        _domain_role = await DomainRole.get_or_none(domain=domain.id, role=domain_role)
    else:
        _domain_role = None
    if _domain_role:
        return DomainPermission(**_domain_role.permission)
    elif domain_role in DEFAULT_DOMAIN_PERMISSION:
        return DEFAULT_DOMAIN_PERMISSION[DefaultRole(domain_role)]
    else:
        return DEFAULT_DOMAIN_PERMISSION[DefaultRole.GUEST]


def is_domain_permission(scope: ScopeType) -> bool:
    return scope in (
        ScopeType.DOMAIN_GENERAL,
        ScopeType.DOMAIN_PROBLEM,
        ScopeType.DOMAIN_PROBLEM_SET,
        ScopeType.DOMAIN_RECORD,
    )


class Authentication:
    def __init__(
        self,
        jwt_decoded: Optional[JWTToken] = Depends(auth_jwt_decode),
        user: User = Depends(get_current_user),
        site_role: str = Depends(get_site_role),
        site_permission: SitePermission = Depends(get_site_permission),
    ):
        self.jwt: Optional[JWTToken] = jwt_decoded
        self.user: User = user
        self.site_role: str = site_role
        self.site_permission: SitePermission = site_permission
        self.domain: Optional[Domain] = None
        self.domain_role: str = DefaultRole.GUEST
        self.domain_permission: DomainPermission = DEFAULT_DOMAIN_PERMISSION[
            DefaultRole.GUEST
        ]

    def check(self, scope: ScopeType, permission: PermissionType) -> bool:
        def _check(permissions: Optional[Dict[str, Any]]) -> bool:
            if permissions is None:
                return False
            return permissions.get(permission, False)

        # grant site root with all permissions
        if self.site_role == DefaultRole.ROOT:
            return True
        # grant domain root with domain permissions
        if self.domain_role == DefaultRole.ROOT and is_domain_permission(scope):
            return True
        # grant permission if site permission found
        if self.site_permission and _check(
            self.site_permission.dict().get(scope, None)
        ):
            return True
        # grant permission if domain permission found
        if self.domain_permission and _check(
            self.domain_permission.dict().get(scope, None)
        ):
            return True
        # permission denied if every check failed
        return False

    def is_root(self) -> bool:
        return self.site_role == DefaultRole.ROOT

    def is_domain_root(self) -> bool:
        return (
            self.is_root()
            or self.domain_role == DefaultRole.ROOT
            or self.is_domain_owner()
        )

    def is_domain_owner(self) -> bool:
        if self.domain is None:
            return False
        return self.domain.owner.pk == self.user.id


class DomainAuthentication:
    def __init__(
        self,
        auth: Authentication = Depends(),
        domain: Domain = Depends(get_domain),
        domain_role: DefaultRole = Depends(get_domain_role),
        domain_permission: DomainPermission = Depends(get_domain_permission),
    ):
        self.auth = auth
        self.auth.domain = domain
        self.auth.domain_role = domain_role
        self.auth.domain_permission = domain_permission


class PermKey(NamedTuple):
    scope: ScopeType
    permission: PermissionType


class PermCompose(BaseModel):
    permissions: List[Union["PermCompose", PermKey]]
    action: Literal["AND", "OR"] = "AND"


PermCompose.update_forward_refs()
PermKeyTuple = Tuple[ScopeType, PermissionType]
PermComposeIterable = List[  # type: ignore
    Union[PermKey, PermCompose, PermKeyTuple, "PermComposeTuple"]  # type: ignore
]
PermComposeTuple = Union[  # type: ignore
    PermComposeIterable,
    Tuple[PermComposeIterable],
    Tuple[PermComposeIterable, Literal["AND", "OR"]],
]
PermArg1 = (
    Union[
        ScopeType,
        PermComposeIterable,
        PermKey,
        PermCompose,
        PermKeyTuple,
        PermComposeTuple,
    ],
)
PermArg2 = Union[PermissionType, Optional[Literal["AND", "OR"]]]


class PermissionChecker:
    def __init__(self, perm: Union[PermKey, PermCompose]):
        self.perm = perm

    def ensure(self, auth: Authentication, perm: Union[PermKey, PermCompose]) -> None:
        if not isinstance(self.perm, PermKey) and not isinstance(
            self.perm, PermCompose
        ):
            raise InternalServerError(message="Permission Definition Error!")
        result = self.check(auth, perm)
        if result is not None:
            raise ForbiddenError(
                message=f"{result.scope} {result.permission} Permission Denied."
            )

    def check(
        self, auth: Authentication, perm: Union[PermKey, PermCompose]
    ) -> Optional[PermKey]:
        if isinstance(perm, PermKey):
            if auth.check(perm.scope, perm.permission):
                return None
            else:
                return perm

        for child in perm.permissions:
            result = self.check(auth, child)
            if result is None and perm.action == "OR":
                return None
            elif result is not None and perm.action == "AND":
                return result

        if perm.action == "OR":
            return PermKey(ScopeType.UNKNOWN, PermissionType.unknown)
        elif perm.action == "AND":
            return None

        return PermKey(ScopeType.UNKNOWN, PermissionType.unknown)


class UserPermissionChecker(PermissionChecker):
    def __call__(self, auth: Authentication = Depends(Authentication)) -> None:
        self.ensure(auth, self.perm)


class DomainPermissionChecker(PermissionChecker):
    def __call__(
        self, domain_auth: DomainAuthentication = Depends(DomainAuthentication)
    ) -> None:
        self.ensure(domain_auth.auth, self.perm)


def ensure_permission(
    arg1: PermArg1 = None, arg2: PermArg2 = None  # type: ignore
) -> Optional[Callable[..., None]]:
    """
    Returns a permission check dependency in fastapi.
    Support flexible formats:

    (0) Example of no permission (but require login)
        ensure_permission()

    (1) Example of one permission
        ensure_permission(ScopeType, PermissionType)
        ensure_permission((ScopeType, PermissionType))
        ensure_permission([(ScopeType, PermissionType)])

    (2) Example of two permission with operator AND
        ensure_permission([(ScopeType1, PermissionType1), (ScopeType2, PermissionType2)])
        ensure_permission([(ScopeType1, PermissionType1), (ScopeType2, PermissionType2)], "AND")

    (3) Example of two permission with operator OR
        ensure_permission([(ScopeType1, PermissionType1), (ScopeType2, PermissionType2)], "OR")

    (4) Example of complex permissions
        ensure_permission(
            [
                ([(ScopeType1, PermissionType1), (ScopeType2, PermissionType2)], "AND"),
                [(ScopeType3, PermissionType3), (ScopeType4, PermissionType4), (ScopeType5, PermissionType5)],
            ],
            "OR"
        )
    """

    def construct_perm(
        _arg1: PermArg1, _arg2: PermArg2 = None  # type: ignore
    ) -> Union[PermKey, PermCompose]:
        _perm: Optional[Union[PermKey, PermCompose]] = None
        if _arg1 is None:
            if _arg2 is None:
                _perm = PermCompose(permissions=[], action="AND")
        elif isinstance(_arg1, ScopeType) and isinstance(_arg2, PermissionType):
            # accept (scope, permission)
            _perm = PermKey(_arg1, _arg2)
        elif isinstance(_arg1, (PermKey, PermCompose)):
            # accept initialized PermKey and PermCompose
            if _arg2 is None:
                _perm = _arg1
        elif isinstance(_arg1, tuple):
            # split tuple parentheses
            if len(_arg1) == 1:
                _perm = construct_perm(_arg1[0])
            elif len(_arg1) == 2:
                _perm = construct_perm(_arg1[0], _arg1[1])
        else:
            # accept (permissions, action)
            try:
                if _arg2 is None:
                    _arg2 = "AND"
                if _arg2 in ("AND", "OR"):
                    perms = []
                    for child in _arg1:
                        perms.append(construct_perm(child))
                    if len(perms) == 1:
                        _perm = perms[0]
                    else:
                        _perm = PermCompose(permissions=perms, action=_arg2)
            except TypeError:
                pass
        if _perm is None:
            raise ValueError(
                "Permission Initialization failed for {}, {}.".format(_arg1, _arg2)
            )
        return _perm

    def contains_domain(_perm: Union[PermKey, PermCompose]) -> bool:
        if isinstance(_perm, PermKey):
            return is_domain_permission(_perm.scope)
        for child in _perm.permissions:
            if contains_domain(child):
                return True
        return False

    perm = construct_perm(arg1, arg2)
    if contains_domain(perm):
        return DomainPermissionChecker(perm)
    else:
        return UserPermissionChecker(perm)
