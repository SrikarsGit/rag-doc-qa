from openai import OpenAI, embeddings 
from llama_index.readers.file import PDFReader 
from llama_index.core.node_parser import SentenceSplitter 
from config import settings
from pathlib import Path

openai_client = OpenAI(
    api_key=settings.openai_api_key
)

EMBED_MODEL = "text-embedding-3-large"
EMBED_DIM = 3072

splitter = SentenceSplitter(chunk_size=1000, chunk_overlap=200)

def load_and_chunk_pdf(path: Path) -> list[str]:

    # Load pdf content as Document object for each page 
    docs = PDFReader().load_data(file=path)                      
    
    # Extract text-only content from each Document object
    texts = [d.text for d in docs if getattr(d, "text", None)]   
    
    # Chunk texts    
    chunks = []
    
    for text in texts:
        chunks.extend(splitter.split_text(text))
    
    return chunks

def embed_chunks(chunks: list[str]) -> list[list[float]]:
    response = openai_client.embeddings.create(
        model=EMBED_MODEL,
        input=chunks
    )
    return [item.embedding for item in response.data]


def main():
    chunks = load_and_chunk_pdf(Path("C:\\Users\\srika\\Downloads\\Admit Card.pdf"))
    print(chunks)
    print("---------")
    print("Number of chunks: ", len(chunks))
    print("---------")
    print("Embeddings:")
    print(embed_chunks(chunks))

if __name__ == "__main__":
    main()
