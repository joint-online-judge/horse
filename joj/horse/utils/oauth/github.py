from typing import Any, Dict, List, Tuple, cast

import httpx
from typing_extensions import TypedDict

from joj.horse.utils.oauth import BaseOAuth2, GetProfileError, OAuth2Profile

AUTHORIZE_ENDPOINT = "https://github.com/login/oauth/authorize"
ACCESS_TOKEN_ENDPOINT = "https://github.com/login/oauth/access_token"
BASE_SCOPES = ["user:email"]
PROFILE_ENDPOINT = "https://api.github.com/user"
EMAILS_ENDPOINT = "https://api.github.com/user/emails"


class GitHubOAuth2AuthorizeParams(TypedDict, total=False):
    login: str
    allow_signup: bool


class GitHubOAuth2(BaseOAuth2[GitHubOAuth2AuthorizeParams]):
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        name: str = "github",
        display_name: str = "GitHub",
        icon: str = "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png",
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
        async with httpx.AsyncClient(
            headers={
                **self.request_headers,
                "Authorization": f"token {token['access_token']}",
            }
        ) as client:
            response = await client.get(PROFILE_ENDPOINT)

            if response.status_code >= 400:
                raise GetProfileError(response.json())

            data = cast(Dict[str, Any], response.json())

            account_email = data["email"]

            # No public email, make a separate call to /user/emails
            if account_email is None:
                response = await client.get(EMAILS_ENDPOINT)

                if response.status_code >= 400:
                    raise GetProfileError(response.json())

                emails = cast(List[Dict[str, Any]], response.json())

                account_email = emails[0]["email"]

            return (
                OAuth2Profile(
                    oauth_name=self.name,
                    account_id=data["id"],
                    account_name=data["login"],
                    account_email=account_email,
                    # real_name=data["name"],
                    # student_id=data["code"],
                ),
                data,
            )
