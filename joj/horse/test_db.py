import asyncio
from joj.horse.utils.db import get_db, ensure_indexes
from joj.horse.models.domain import Domain
from joj.horse.models.user import User, UserReference

from bson import ObjectId


async def main():
    get_db()
    await ensure_indexes()
    # domain = Domain(owner=UserReference(id="5f3c2954e192d3d412b0190d"))
    # await domain.owner.populate()
    # print(domain.owner.data)
    # await domain.save()

    domain = await Domain.find_one()
    print(domain.owner)


if __name__ == '__main__':
    asyncio.run(main())
