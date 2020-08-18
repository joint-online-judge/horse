import uuid
from typing import Optional

from pydantic import BaseModel


class Session(BaseModel):
    key: uuid.UUID
    oauth_state: Optional[str] = ''

    uid: str = ''
    name: str = ''
