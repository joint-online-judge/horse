import uuid
from typing import Optional

from pydantic import BaseModel

from joj.horse.models.user import User


class Session(BaseModel):
    key: uuid.UUID
    oauth_state: Optional[str] = ''
    oauth_provider: Optional[str] = ''

    user: User = None
