from functools import lru_cache
from typing import Optional

import oauth_jaccount

from joj.horse.config import settings
from joj.horse.schemas import BaseModel


@lru_cache()
def get_client() -> Optional[oauth_jaccount.JaccountClient]:
    if not settings.oauth_jaccount:
        return None
    return oauth_jaccount.JaccountClient(
        settings.oauth_jaccount_id, settings.oauth_jaccount_secret
    )


class IDToken(BaseModel):
    aud: str  # client_id
    iss: str  # 'https://jaccount.sjtu.edu.cn/oauth2/'
    sub: str  # jaccount username
    exp: str  # expiration time (UNIX epoch)
    iat: str  # issue time (UNIX epoch)
    name: str  # real name
    code: str  # seems empty?
    type: str  # jaccount type (student/faculty/alumni)
