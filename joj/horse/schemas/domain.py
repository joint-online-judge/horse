from typing import Optional, Union

from pydantic import BaseModel

from joj.horse import schemas
from joj.horse.utils.db import PydanticObjectId


class Domain(BaseModel):
    class Config:
        orm_mode = True

    id: Optional[PydanticObjectId]

    url: str
    name: str
    owner: Union[PydanticObjectId, schemas.User]

    gravatar: str = ""
    bulletin: str = ""
