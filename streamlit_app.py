import asyncio
from pathlib import Path
import time
import streamlit as st
import inngest
from dotenv import load_dotenv
import os
import requests
import tempfile

load_dotenv()

st.set_page_config(page_title="RAG Ingest PDF", page_icon="📄", layout="centered")


@st.cache_resource
def get_inngest_client() -> inngest.Inngest:
    return inngest.Inngest(app_id="A RAG Application", is_production=False)


if "answer" not in st.session_state:
    st.session_state.answer = ""
if "sources" not in st.session_state:
    st.session_state.sources = []
if "uploaded_docs" not in st.session_state:
    st.session_state.uploaded_docs = []
if "uploaded_paths" not in st.session_state:
    st.session_state.uploaded_paths = []
if "clear_warning" not in st.session_state:
    st.session_state.clear_warning = ""


def save_uploaded_pdf(file) -> Path:
    suffix = Path(file.name).suffix or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(file.getbuffer())
        return Path(temp_file.name)


def clear_uploaded_pdfs() -> list[str]:
    locked_files = []
    for pdf_path_str in st.session_state.uploaded_paths:
        pdf_path = Path(pdf_path_str)
        if not pdf_path.exists():
            continue
        try:
            pdf_path.unlink()
        except PermissionError:
            locked_files.append(pdf_path.name)
    return locked_files


async def send_rag_ingest_event(pdf_path: Path, source_id: str) -> None:
    client = get_inngest_client()
    await client.send(
        inngest.Event(
            name="rag/ingest_pdf",
            data={
                "pdf_path": str(pdf_path.resolve()),
                "source_id": source_id,
            },
        )
    )


st.title("Upload a PDF to Ingest")
uploaded = st.file_uploader("Choose a PDF", type=["pdf"], accept_multiple_files=False)

if uploaded is not None:
    with st.spinner("Uploading and triggering ingestion..."):
        path = save_uploaded_pdf(uploaded)
        # Kick off the event and block until the send completes
        asyncio.run(send_rag_ingest_event(path, uploaded.name))
        # Small pause for user feedback continuity
        time.sleep(0.3)
    if uploaded.name not in st.session_state.uploaded_docs:
        st.session_state.uploaded_docs.append(uploaded.name)
    if str(path) not in st.session_state.uploaded_paths:
        st.session_state.uploaded_paths.append(str(path))
    st.success(f"Triggered ingestion for: {uploaded.name}")
    st.caption("You can upload another PDF if you like.")

if st.session_state.uploaded_docs:
    st.caption("Uploaded docs")
    for doc_name in st.session_state.uploaded_docs:
        st.write(f"- {doc_name}")

if st.session_state.clear_warning:
    st.warning(st.session_state.clear_warning)
    st.session_state.clear_warning = ""

st.divider()
st.title("Ask a question about your PDFs")


async def send_rag_query_event(question: str, top_k: int) -> None:
    client = get_inngest_client()
    result = await client.send(
        inngest.Event(
            name="rag/query_pdf_ai",
            data={
                "question": question,
                "top_k": top_k,
            },
        )
    )

    return result[0]


def _inngest_api_base() -> str:
    # Local dev server default; configurable via env
    return os.getenv("INNGEST_API_BASE", "http://127.0.0.1:8288/v1")


def fetch_runs(event_id: str) -> list[dict]:
    url = f"{_inngest_api_base()}/events/{event_id}/runs"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", [])


def wait_for_run_output(event_id: str, timeout_s: float = 120.0, poll_interval_s: float = 0.5) -> dict:
    start = time.time()
    last_status = None
    while True:
        runs = fetch_runs(event_id)
        if runs:
            run = runs[0]
            status = run.get("status")
            last_status = status or last_status
            if status in ("Completed", "Succeeded", "Success", "Finished"):
                return run.get("output") or {}
            if status in ("Failed", "Cancelled"):
                raise RuntimeError(f"Function run {status}")
        if time.time() - start > timeout_s:
            raise TimeoutError(f"Timed out waiting for run output (last status: {last_status})")
        time.sleep(poll_interval_s)


with st.form("rag_query_form"):
    question = st.text_input("Your question")
    top_k = st.number_input("How many chunks to retrieve", min_value=1, max_value=20, value=5, step=1)
    submitted = st.form_submit_button("Ask")

    if submitted and question.strip():
        with st.spinner("Sending event and generating answer..."):
            # Fire-and-forget event to Inngest for observability/workflow
            event_id = asyncio.run(send_rag_query_event(question.strip(), int(top_k)))
            # Poll the local Inngest API for the run's output
            output = wait_for_run_output(event_id)
            st.session_state.answer = output.get("answer", "")
            st.session_state.sources = output.get("sources", [])

if st.button("Clear response and uploaded docs"):
    st.session_state.answer = ""
    st.session_state.sources = []
    st.session_state.uploaded_docs = []
    locked_files = clear_uploaded_pdfs()
    st.session_state.uploaded_paths = []
    if locked_files:
        st.session_state.clear_warning = (
            "Some uploaded PDFs could not be deleted because they are still in use: "
            + ", ".join(locked_files)
        )
    st.rerun()

if st.session_state.answer:
    st.subheader("Answer")
    st.write(st.session_state.answer)
elif st.session_state.sources:
    st.subheader("Answer")
    st.write("(No answer)")

if st.session_state.sources:
    st.caption("Sources")
    for s in st.session_state.sources:
        st.write(f"- {s}")
