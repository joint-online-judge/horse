import asyncio

from joj.horse.models.domain import Domain
from joj.horse.utils.db import ensure_indexes, get_db


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
