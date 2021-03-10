from functools import lru_cache

import oauth_jaccount
from pydantic import BaseModel

from joj.horse.config import settings


@lru_cache()
def get_client() -> oauth_jaccount.JaccountClient:
    if not settings.oauth_jaccount:
        return None
    return oauth_jaccount.JaccountClient(
        settings.oauth_jaccount_id, settings.oauth_jaccount_secret
    )


class IDToken(BaseModel):
    aud: str
    iss: str
    sub: str
    exp: str
    iat: str
    name: str
    code: str
    type: str
