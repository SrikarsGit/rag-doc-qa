from os import name

import asyncpg
from app.config import settings


# Create connection pooling with asyncpg
async def create_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        min_size=2,
        max_size=10
    )





