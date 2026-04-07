import asyncio
from db import init_orm, close_orm


async def main():
    await init_orm()
    await close_orm()


if __name__ == "__main__":
    asyncio.run(main())