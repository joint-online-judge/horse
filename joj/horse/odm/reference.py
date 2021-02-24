from typing import Optional, Type, Union

from bson import ObjectId
from pydantic import BaseModel, validator

from .document import Document


class Reference(BaseModel):
    id: Union[ObjectId, str]
    data: Optional[Document] = None
    reference: Type[Document] = Document

    @validator("id", allow_reuse=True, pre=True)
    def validate_id(cls, v):
        if isinstance(v, str):
            return ObjectId(v)
        elif isinstance(v, ObjectId):
            return v
        else:
            raise ValueError("error")

    async def populate(self):
        self.data = await self.reference.find_by_id(self.id)
        return self.data

    def dict(self, **kwargs):
        return {"id": self.id}
