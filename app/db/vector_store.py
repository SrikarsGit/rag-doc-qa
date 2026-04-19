from asyncpg import Pool
import json 

async def upsert(pool: Pool, ids, payloads, vecs) -> None:

    if not (len(ids) == len(payloads) == len(vecs)):
        raise ValueError("ids, payloads, and vecs must have the same length")
    
    vecs = list(str(v) for v in vecs)
    payloads = list(json.dumps(payload) for payload in payloads)
    data = list(zip(ids, payloads, vecs))

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
            if isinstance(payload, str):
                payload = json.loads(payload)
            text = payload.get("text")
            source = payload.get("source")

            if text:
                context.append(text)
            if source:
                sources.add(source)

        return {"contexts": context, "sources": list(sources)}


