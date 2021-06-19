from hashlib import sha512
from typing import Any, Callable, Optional

from gridfs.errors import NoFile
from motor.core import AgnosticCollection
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from motor.motor_gridfs import AgnosticGridFSBucket, AgnosticGridOut
from umongo.frameworks.motor_asyncio import MotorAsyncIOInstance


class GridFSHashStorage:
    def __init__(
        self,
        instance: MotorAsyncIOInstance,
        bucket_name: str,
        hash_function: Callable[[bytes], Any] = sha512,
    ) -> None:
        self.instance = instance
        self.bucket_name = bucket_name
        self.bucket: AgnosticGridFSBucket = AsyncIOMotorGridFSBucket(
            self.instance.db, bucket_name=bucket_name, disable_md5=True
        )
        self.hash_function = hash_function
        self.files: AgnosticCollection = self.instance.db.get_collection(
            bucket_name + ".files"
        )

    async def read(self, digest: str) -> bytes:
        async with self.instance.session() as session:
            grid_out: AgnosticGridOut = await self.bucket.open_download_stream_by_name(
                digest, session=session
            )
            return await grid_out.read()

    async def write(self, data: bytes, digest: Optional[str] = None) -> bool:
        """
        if file is really uploaded, return True; else, return False
        """
        async with self.instance.session() as session:
            if digest is None:
                digest = self.hash_function(data).hexdigest()
            file = await self.files.find_one({"filename": digest}, session=session)
            file_not_found = file is None
            if file_not_found:
                await self.bucket.upload_from_stream(digest, data, session=session)
            return file_not_found

    async def delete(self, digest: str) -> bool:
        """
        if file is really deleted, return True; else, return False
        """
        async with self.instance.session() as session:
            file = await self.files.find_one({"filename": digest}, session=session)
            if file:
                try:
                    await self.bucket.delete(file["_id"], session=session)
                except NoFile:
                    return False
                return True
            return False
