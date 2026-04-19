from openai import AsyncOpenAI
from llama_index.readers.file import PDFReader 
from llama_index.core.node_parser import SentenceSplitter 
from app.config import settings
from pathlib import Path

openai_client = AsyncOpenAI(
    api_key=settings.openai_api_key
)

EMBED_MODEL = "text-embedding-3-large"
EMBED_DIM = 3072

splitter = SentenceSplitter(chunk_size=1000, chunk_overlap=200)

def _sanitize_text(text: str) -> str:
    return text.replace("\x00", "")

def load_and_chunk_pdf(path: Path) -> list[str]:

    # Load pdf content as Document object for each page 
    docs = PDFReader().load_data(file=path)                      
    
    # Extract text-only content from each Document object
    texts = [_sanitize_text(d.text) for d in docs if getattr(d, "text", None)]   
    
    # Chunk extracted texts     
    chunks = []

    for text in texts:
        chunks.extend(_sanitize_text(chunk) for chunk in splitter.split_text(text))
    
    return chunks

async def embed_chunks(chunks: list[str]) -> list[list[float]]:
    response = await openai_client.embeddings.create(
        model=EMBED_MODEL,
        input=chunks
    )
    return [item.embedding for item in response.data]

