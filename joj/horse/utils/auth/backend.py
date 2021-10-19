from typing import TYPE_CHECKING, Any, Generic, Optional, TypeVar
from urllib.parse import quote_plus

from fastapi import Response
from fastapi.security import APIKeyCookie, OAuth2PasswordBearer
from fastapi.security.base import SecurityBase
from fastapi_jwt_auth import AuthJWT

from joj.horse.utils.auth import auth_jwt_encode_user
from joj.horse.utils.oauth import OAuth2Profile

if TYPE_CHECKING:
    from joj.horse.models.user import User

T = TypeVar("T")


class BaseAuthentication(Generic[T]):
    """
    Base authentication backend.
    Every backend should derive from this class.
    :param name: Name of the backend.
    :param logout: Whether or not this backend has a logout process.
    """

    scheme: SecurityBase
    name: str
    logout: bool

    def __init__(self, name: str = "base", logout: bool = False):
        self.name = name
        self.logout = logout

    # async def __call__(
    #     self,
    #     credentials: Optional[T],
    # ) -> Any:
    #     raise NotImplementedError()

    async def get_login_response(
        self,
        auth_jwt: AuthJWT,
        user: Optional["User"],
        oauth2_profile: Optional[OAuth2Profile],
        redirect_url: str,
        response: Response,
    ) -> None:
        raise NotImplementedError()

    async def get_logout_response(
        self,
        auth_jwt: AuthJWT,
        user: Optional["User"],
        oauth2_profile: Optional[OAuth2Profile],
        redirect_url: str,
        response: Response,
    ) -> None:
        raise NotImplementedError()


class CookieAuthentication(BaseAuthentication[str]):
    """
    Authentication backend using a cookie.
    Internally, uses a JWT token to store the data.
    """

    cookie_name: str
    scheme: APIKeyCookie

    def __init__(
        self,
        name: str = "cookie",
        cookie_name: str = "access_token_cookie",
    ):
        super().__init__(name, logout=True)
        self.cookie_name = cookie_name
        self.scheme = APIKeyCookie(name=self.cookie_name, auto_error=False)

    # async def __call__(
    #     self,
    #     credentials: Optional[str],
    #     user_manager: BaseUserManager[models.UC, models.UD],
    # ) -> Optional[models.UD]:
    #     if credentials is None:
    #         return None
    #
    #     try:
    #         data = decode_jwt(credentials, self.secret, self.token_audience)
    #         user_id = data.get("user_id")
    #         if user_id is None:
    #             return None
    #     except jwt.PyJWTError:
    #         return None
    #
    #     try:
    #         user_uiid = UUID4(user_id)
    #         return await user_manager.get(user_uiid)
    #     except ValueError:
    #         return None
    #     except UserNotExists:
    #         return None

    async def get_login_response(
        self,
        auth_jwt: AuthJWT,
        user: Optional["User"],
        oauth2_profile: Optional[OAuth2Profile],
        redirect_url: str,
        response: Response,
    ) -> None:
        token = auth_jwt_encode_user(auth_jwt, user, oauth2_profile)
        print(token)
        auth_jwt.set_access_cookies(token, response)
        if redirect_url:
            response.status_code = 307
            response.headers["location"] = quote_plus(
                str(redirect_url), safe=":/%#?&=@[]!$&'()*+,;"
            )

    async def get_logout_response(
        self,
        auth_jwt: AuthJWT,
        user: Optional["User"],
        oauth2_profile: Optional[OAuth2Profile],
        redirect_url: str,
        response: Response,
    ) -> None:
        auth_jwt.unset_access_cookies(response)


class JWTAuthentication(BaseAuthentication[str]):
    """
    Authentication backend using a JWT in a Bearer header.
    """

    scheme: OAuth2PasswordBearer

    def __init__(
        self,
        token_url: str = "auth/jwt/login",
        name: str = "jwt",
    ):
        super().__init__(name, logout=False)
        self.scheme = OAuth2PasswordBearer(token_url, auto_error=False)

    # async def __call__(
    #     self,
    #     credentials: Optional[str],
    #     user_manager: BaseUserManager[models.UC, models.UD],
    # ) -> Optional[models.UD]:
    #     if credentials is None:
    #         return None
    #
    #     try:
    #         data = decode_jwt(credentials, self.secret, self.token_audience)
    #         user_id = data.get("user_id")
    #         if user_id is None:
    #             return None
    #     except jwt.PyJWTError:
    #         return None
    #
    #     try:
    #         user_uiid = UUID4(user_id)
    #         return await user_manager.get(user_uiid)
    #     except ValueError:
    #         return None
    #     except UserNotExists:
    #         return None

    async def get_login_response(
        self,
        auth_jwt: AuthJWT,
        user: Optional["User"],
        oauth2_profile: Optional[OAuth2Profile],
        redirect_url: str,
        response: Response,
    ) -> Any:
        token = auth_jwt_encode_user(auth_jwt, user, oauth2_profile)
        return {"access_token": token, "token_type": "bearer"}

    async def get_logout_response(
        self,
        auth_jwt: AuthJWT,
        user: Optional["User"],
        oauth2_profile: Optional[OAuth2Profile],
        redirect_url: str,
        response: Response,
    ) -> None:
        raise NotImplementedError()
