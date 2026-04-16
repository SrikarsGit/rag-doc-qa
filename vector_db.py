import asyncio
import asyncpg
import datetime 
from config import settings

async def main():

    conn = await asyncpg.connect(
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        host=settings.db_host,
        port=settings.db_port
    )

    print("Connected to DB!")



    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sample(
            id INT,
            name TEXT
        );        
    """
    )

    data = [
    (1, "apple"),
    (2, "banana")
]


    await conn.executemany(
        """
        INSERT INTO sample 
        VALUES ($1, $2);
    """, data
    )

    rows = await conn.fetch(
        """ SELECT * FROM sample; """
    )

    for row in rows:
        print(dict(row))

    
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

