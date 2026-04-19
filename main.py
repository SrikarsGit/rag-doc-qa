import logging 
from fastapi import FastAPI 
import inngest 
import inngest.fast_api
from inngest.experimental import ai
from dotenv import load_dotenv
import uuid 
import os 
from pathlib import Path
import datetime 
from config import settings
from contextlib import asynccontextmanager
from openai import embeddings
from db.pool import create_pool
from db.vector_store import upsert, search
from data_loader import load_and_chunk_pdf, embed_chunks
from model import RAGChunkAndSrc, RAGUpsertResult, RAGQueryResult, RAGSearchResult

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db_pool = await create_pool()
    try:
        yield 
    finally:
        await app.state.db_pool.close()

# Inggest dev server initialization
inngest_client = inngest.Inngest(
    app_id="A RAG Application",
    logger=logging.getLogger("uvicorn"),
    is_production=False,
    serializer=inngest.PydanticSerializer()
)

# Initialize fastapi app with lifespan
app = FastAPI(lifespan=lifespan)


@inngest_client.create_function(
        fn_id="RAG: Ingest PDF",
        trigger=inngest.TriggerEvent(event="rag/ingest_pdf")
)
async def rag_ingest_pdf(ctx: inngest.Context):

    def _load(ctx) -> RAGChunkAndSrc:
        file_path = ctx.event.data["pdf_path"]
        source_id = ctx.event.data.get("source_id", file_path)
        chunks = load_and_chunk_pdf(path=Path(file_path))
      
        return RAGChunkAndSrc(chunks=chunks, source_id=source_id)
    
    async def _upsert(chunks_and_src: RAGChunkAndSrc) -> RAGUpsertResult:
        chunks = chunks_and_src.chunks
        source_id = chunks_and_src.source_id
        
        doc_ids = [uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{i}") for i in range(len(chunks))]
        embeddings = await embed_chunks(chunks)
        payloads = [{"source": source_id, "text": chunks[i]} for i in range(len(chunks))] 
        
        await upsert(pool=app.state.db_pool, ids=doc_ids, payloads=payloads, vecs=embeddings)

        return RAGUpsertResult(ingested=len(chunks)) 
    
    chunks_and_src = await ctx.step.run("load-and-chunk", lambda: _load(ctx), output_type=RAGChunkAndSrc)
    ingested = await ctx.step.run("embed-and-upsert", lambda: _upsert(chunks_and_src), output_type=RAGUpsertResult)

    return ingested.model_dump()


@inngest_client.create_function(
    fn_id="RAG: Query PDF",
    trigger=inngest.TriggerEvent(event="rag/query_pdf_ai")
)
async def rag_query_pdf_ai(ctx: inngest.Context):

    async def _search(question: str, top_k: int = 5) -> RAGSearchResult:
        query_vec = await embed_chunks([question])
        result = await search(pool=app.state.db_pool, query_vector=query_vec[0], top_k=top_k)

        return RAGSearchResult(
            contexts=result["contexts"],
            sources=result["sources"]
        )
    
    question = ctx.event.data["question"]
    top_k = int(ctx.event.data.get("top_k", 5))
    found = await ctx.step.run("embed-and-search", lambda: _search(question, top_k), output_type=RAGSearchResult)
    
    context_block = "\n\n".join(f'- {c}' for c in found.contexts)
    
    user_content = f"""
    You are a question-answering assistant.

    Follow these rules strictly:
    1. Answer ONLY using the provided context.
    2. If the answer is not in the context, say "I don't know".
    3. Do NOT use prior knowledge.
    4. Cite the relevant parts of the context in your answer.

    ---------------------
    Context:
    {context_block}
    ---------------------

    Question:
    {question}

    Answer:
    """

    response = await ctx.step.ai.infer(
        step_id="LLM-Response",
        
        adapter=ai.openai.Adapter(
            model= "gpt-4o-mini",
            auth_key= settings.openai_api_key
        ),

        body={
            "max_tokens": 1024,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": "You are a RAG assistant and your job is to answer questions using only the provided context"},
                {"role": "user", "content": user_content}
            ]
        }
    )

    answer = response["choices"][0]["message"]["content"].strip()
    
    result = RAGQueryResult(
        answer=answer,
        sources=found.sources,
        num_contexts=len(found.contexts)
    )

    return result.model_dump() 

inngest.fast_api.serve(app, inngest_client, [rag_ingest_pdf, rag_query_pdf_ai]) 

