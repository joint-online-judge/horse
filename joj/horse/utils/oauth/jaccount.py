from typing import Any, Dict, Tuple, cast

import httpx
from typing_extensions import TypedDict

from joj.horse.schemas import BaseModel
from joj.horse.utils.oauth import BaseOAuth2, GetProfileError, OAuth2Profile

AUTHORIZE_ENDPOINT = "https://jaccount.sjtu.edu.cn/oauth2/authorize"
ACCESS_TOKEN_ENDPOINT = "https://jaccount.sjtu.edu.cn/oauth2/token"
BASE_SCOPES = ["basic"]
PROFILE_ENDPOINT = "https://api.sjtu.edu.cn/v1/me/profile"


class JaccountOAuth2AuthorizeParams(TypedDict, total=False):
    ...


class JaccountOAuth2(BaseOAuth2[JaccountOAuth2AuthorizeParams]):
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        name: str = "jaccount",
        display_name: str = "JAccount",
        icon: str = "https://vi.sjtu.edu.cn/img/base/Logo.png",
    ):
        super().__init__(
            client_id,
            client_secret,
            AUTHORIZE_ENDPOINT,
            ACCESS_TOKEN_ENDPOINT,
            name=name,
            base_scopes=BASE_SCOPES,
            display_name=display_name,
            icon=icon,
        )

    async def get_profile(
        self, token: Dict[str, Any]
    ) -> Tuple[OAuth2Profile, Dict[str, Any]]:
        async with httpx.AsyncClient(headers=self.request_headers) as client:
            response = await client.get(
                PROFILE_ENDPOINT, params={"access_token": token["access_token"]}
            )

            if response.status_code >= 400:
                raise GetProfileError(
                    str(response) + " " + response.content.decode("utf-8")
                )

            try:
                data = cast(Dict[str, Any], response.json())
                data = data["entities"][0]

                return (
                    OAuth2Profile(
                        oauth_name=self.name,
                        account_id=data["id"],
                        account_name=data["account"],
                        account_email=data["account"] + "@sjtu.edu.cn",
                        real_name=data["name"],
                        student_id=data["code"],
                    ),
                    data,
                )
            except Exception:
                raise GetProfileError(response.content.decode("utf-8"))


class IDToken(BaseModel):
    aud: str  # client_id
    iss: str  # 'https://jaccount.sjtu.edu.cn/oauth2/'
    sub: str  # jaccount username
    exp: str  # expiration time (UNIX epoch)
    iat: str  # issue time (UNIX epoch)
    name: str  # real name
    code: str  # seems empty?
    type: str  # jaccount type (student/faculty/alumni)
