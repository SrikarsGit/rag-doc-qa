from asyncpg import Pool

async def upsert(pool: Pool, data: list[list]) -> None:

    for d in data:
        d[-1] = f'{d[-1]}'

    async with pool.acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO documents (doc_id, payload, embedding)
            VALUES ($1, $2, $3) 
            ON CONFLICT(doc_id) 
            DO UPDATE 
            SET 
                payload = EXCLUDED.payload, 
                embedding = EXCLUDED.embedding;
            
            """,
            data
        )

async def search(pool: Pool, query_vector: list[float], top_k: int = 5):
    async with pool.acquire() as conn:
        docs = await conn.fetch(
            """
            SELECT doc_id, payload
            FROM documents
            ORDER BY 
            embedding <=> $1
            LIMIT $2
            
            """,
            str(query_vector), top_k
        )
        results = [dict(doc) for doc in docs]

        context = []
        sources = set()

        for result in results:
            payload = result["payload"]
            text = payload.get("text")
            source = payload.get("source")

            if text:
                context.append(text)
                sources.add(source)

        return {"contexts": context, "sources": list(sources)}


