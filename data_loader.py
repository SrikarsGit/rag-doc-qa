from openai import OpenAI 
from llama_index.readers.file import PDFReader 
from llama_index.core.node_parser import SentenceSplitter 
from config import settings

openai_client = OpenAI(
    api_key=settings.openai_api_key
)

EMBED_MODEL = "text-embedding-3-large"
EMBED_DIM = 3072

