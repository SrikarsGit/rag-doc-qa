# PDF RAG Assistant

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Frontend-FF4B4B?logo=streamlit&logoColor=white)
![Inngest](https://img.shields.io/badge/Inngest-Workflow%20Orchestration-000000)
![OpenAI](https://img.shields.io/badge/OpenAI-Embeddings%20%2B%20LLM-412991?logo=openai&logoColor=white)
![Postgres](https://img.shields.io/badge/PostgreSQL-17-4169E1?logo=postgresql&logoColor=white)
![pgvector](https://img.shields.io/badge/pgvector-Vector%20Search-336791)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)

An end-to-end Retrieval-Augmented Generation (RAG) application that ingests PDF documents, stores vector embeddings in PostgreSQL with `pgvector`, and answers user questions through a Streamlit interface using context-grounded LLM responses.

This project demonstrates a practical way to build a modern AI application with:

- asynchronous Python services
- event-driven workflows with Inngest
- vector search with PostgreSQL + `pgvector`
- OpenAI embeddings and generation
- a simple product-facing frontend in Streamlit

## Overview

This is not just a notebook demo. It is a small, production-style system with clear separation between:

- document ingestion
- embedding generation
- vector persistence
- retrieval
- answer generation
- user interface

It includes practical engineering decisions such as:

- event-based orchestration instead of tightly coupled request chains
- typed models with Pydantic
- async database access with connection pooling
- vector search stored in infrastructure the team can actually own
- PDF text sanitization to avoid ingestion failures from malformed input
- a usable frontend for demoing the workflow end to end

## Demo Flow

1. Upload a PDF from the Streamlit UI.
2. Streamlit sends an Inngest event for ingestion.
3. The backend reads the PDF, sanitizes text, splits it into chunks, and generates embeddings with OpenAI.
4. Chunks are stored in PostgreSQL with `pgvector`.
5. Ask a question in the UI.
6. A second Inngest workflow embeds the query, retrieves the top matching chunks, and prompts the model to answer using only retrieved context.
7. The UI displays the grounded answer and the document sources.

## Tech Stack

- Python 3.12
- FastAPI
- Streamlit
- Inngest
- OpenAI API
- PostgreSQL 17
- pgvector
- asyncpg
- Pydantic / pydantic-settings
- LlamaIndex PDF reader and sentence splitter
- Docker Compose
- uv

## Architecture

### 1. Ingestion Workflow

Defined in [app/main.py](app/main.py), the `rag/ingest_pdf` workflow:

- accepts a PDF path and source identifier
- loads and chunks the document via [app/document_ingestion.py](app/document_ingestion.py)
- generates embeddings with `text-embedding-3-large`
- creates deterministic UUIDs per chunk
- upserts chunk payloads and vectors into PostgreSQL

### 2. Retrieval + Answering Workflow

Also defined in [app/main.py](app/main.py), the `rag/query_pdf_ai` workflow:

- embeds the user question
- performs top-k similarity search in PostgreSQL through [app/db/vector_store.py](app/db/vector_store.py)
- constructs a context-grounded prompt
- calls the LLM to generate an answer constrained to retrieved context
- returns the answer, sources, and number of retrieved contexts

### 3. Vector Store

[app/db/vector_store.py](app/db/vector_store.py) is responsible for:

- validating aligned input lengths for IDs, payloads, and vectors
- serializing chunk metadata into `JSONB`
- storing 3072-dimensional embeddings in `pgvector`
- searching by cosine distance using `<=>`

### 4. Frontend

[streamlit_app.py](streamlit_app.py) provides a simple demo UI for:

- uploading PDFs
- triggering ingestion events
- asking questions
- polling Inngest run output
- clearing answers and uploaded temp files

## Project Structure

```text
.
|-- app/
|   |-- config.py
|   |-- document_ingestion.py
|   |-- main.py
|   |-- model.py
|   `-- db/
|       |-- init/
|       |   `-- 01-init.sql
|       |-- pool.py
|       `-- vector_store.py
|-- docker-compose.yml
|-- pyproject.toml
|-- streamlit_app.py
`-- README.md
```

## Data Model

The PostgreSQL schema is initialized by [app/db/init/01-init.sql](app/db/init/01-init.sql):

- `doc_id UUID PRIMARY KEY`
- `payload JSONB`
- `embedding vector(3072)`
- `created_at TIMESTAMP`

This keeps the system simple while still supporting semantic search directly inside PostgreSQL.

## Local Setup

### 1. Clone and Install Dependencies

```bash
git clone <your-repo-url>
cd RAG-project
uv sync
```

### 2. Create `.env`

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key
DB_HOST=127.0.0.1
DB_PORT=5433
DB_NAME=ragdb
DB_USER=raguser
DB_PASSWORD=ragpwd
```

### 3. Start PostgreSQL + pgvector

```bash
docker compose up -d
```

### 4. Start the FastAPI + Inngest App

```bash
uv run uvicorn app.main:app --reload
```

### 5. Start the Inngest Dev Server

```bash
npx inngest-cli@latest dev -u http://127.0.0.1/api/inngest --no-discovery
```

By default, the Streamlit app expects the local Inngest API at:

```text
http://127.0.0.1:8288/v1
```

If needed, override it with:

```env
INNGEST_API_BASE=http://127.0.0.1:8288/v1
```

### 6. Start the Streamlit Frontend

```bash
uv run streamlit run streamlit_app.py
```

## Example Usage

### Ingest a Document

- Open the Streamlit app
- Upload a PDF
- Wait for the ingestion confirmation

### Ask Questions

Try prompts like:

- "What is the main goal of this document?"
- "Summarize the methodology section."
- "Who are the participants in the study?"
- "What evidence does the paper provide for its conclusion?"

## Engineering Notes

### Text Sanitization

PDF extraction can include null characters (`\x00`), which PostgreSQL cannot store in `TEXT` or `JSONB`. This project sanitizes extracted text before chunking and persistence to prevent ingestion failures.

### Deterministic Chunk IDs

Each chunk ID is generated from the source and chunk index, which makes repeated ingestion idempotent and enables clean upserts instead of duplicate inserts.

### Event-Driven Workflows

Inngest decouples UI actions from backend processing. That makes the app easier to evolve toward retries, observability, and more complex document pipelines.

## Key Capabilities

This project includes:

- backend API and workflow orchestration
- AI integration with embeddings + retrieval + generation
- database design for semantic search
- practical debugging of real-world ingestion issues
- clean project organization with typed models and configuration management
- a frontend that makes the workflow easy to use and demonstrate

## Future Improvements

Some natural next steps for this project:

- add HNSW indexing for faster vector retrieval at scale
- support multiple file types beyond PDFs
- add document deletion / reindexing workflows
- add evaluation and answer quality checks
- persist conversation history
- containerize the FastAPI and Streamlit services
- add automated tests for ingestion, retrieval, and prompt behavior
