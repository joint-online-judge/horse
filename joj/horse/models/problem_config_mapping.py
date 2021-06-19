from typing import Any, Dict, Optional, Union

from joj.elephant.schemas import FileType
from pymongo import ASCENDING, IndexModel
from umongo import fields, validate
from umongo.frameworks.motor_asyncio import MotorAsyncIODocument

from joj.horse.models.base import DocumentMixin
from joj.horse.utils.db import GridFSBucket, get_grid_fs, instance


@instance.register
class ProblemConfigMapping(DocumentMixin, MotorAsyncIODocument):
    class Meta:
        collection_name = "problem.config.mappings"
        indexes = [
            IndexModel("digest"),
            IndexModel([("config", ASCENDING), ("path", ASCENDING)], unique=True),
        ]
        strict = False

    config = fields.ObjectIdField(required=True)
    path = fields.StringField(required=True)
    type = fields.StringField(
        required=True, validate=validate.OneOf(list(FileType.__members__.keys()))
    )
    digest = fields.StringField(default="")

    _data: Optional[bytes] = None

    async def read(self) -> Optional[bytes]:
        if self._data is not None:
            self._data = await get_grid_fs(GridFSBucket.problem_config).read(
                self.digest
            )
        return self._data

    async def write(self, data: bytes, digest: Optional[str] = None) -> None:
        grid_fs = get_grid_fs(GridFSBucket.problem_config)
        if digest is None:
            digest = grid_fs.hash_function(data).hexdigest()
        if digest == self.digest:
            return
        await grid_fs.write(data, digest)
        old_digest = self.digest
        self.digest = digest
        self._data = data
        await self.commit()
        if old_digest:
            await self._try_remove_digest(old_digest)

    async def move(
        self, path: Optional[str] = None, type: Optional[Union[str, FileType]] = None
    ) -> None:
        if path is None and type is None:
            return
        if type is not None:
            self.type = str(type)
        if path is not None:
            self.path = path
        await self.commit()

    async def copy(
        self, path: str, file_type: Optional[Union[str, FileType]] = None
    ) -> None:
        if file_type is None:
            file_type = self.type
        else:
            file_type = str(file_type)
        file = ProblemConfigMapping(
            config=self.config, path=path, type=file_type, digest=self.digest
        )
        await file.commit()
        file._data = self._data

    async def delete(self, conditions: Optional[Dict[str, Any]] = None) -> None:
        await self.remove(conditions)

    async def remove(self, conditions: Optional[Dict[str, Any]] = None) -> None:
        await MotorAsyncIODocument.remove(self, conditions)
        await self._try_remove_digest(self.digest)

    @classmethod
    async def find_config_file(
        cls, config: str, path: str
    ) -> Optional["ProblemConfigMapping"]:
        return await cls.find_one({"config": config, "path": path})

    @classmethod
    async def _try_remove_digest(cls, digest: str) -> None:
        mapping = await cls.find_one({"digest": digest})
        if mapping is None:
            await get_grid_fs(GridFSBucket.problem_config).delete(digest)
