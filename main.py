import logging 
from fastapi import FastAPI 
import inngest 
import inngest.fast_api 
from dotenv import load_dotenv
import uuid 
import os 
import datetime 
from contextlib import asynccontextmanager
from db.pool import create_pool

load_dotenv()

inngest_client = inngest.Inngest(
    app_id="A RAG Application",
    logger=logging.getLogger("uvicorn"),
    is_production=False,
    serializer=inngest.PydanticSerializer()
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db_pool = await create_pool()
    try:
        yield 
    finally:
        await app.state.db_pool.close()

app = FastAPI(lifespan=lifespan)

@app.get("/api")
async def default():
    return {"message": "This is a sample endpoint"}

@inngest_client.create_function(
        fn_id="RAG: Ingest PDF",
        trigger=inngest.TriggerEvent(event="rag/ingest_pdf")
)
async def rag_ingest_pdf(ctx: inngest.Context):
    return {"doc": "uploaded!"}

inngest.fast_api.serve(app, inngest_client, [rag_ingest_pdf])


