import hashlib
import uuid
from html import escape
from pathlib import Path

import chromadb
import pymupdf
import streamlit as st

from answer_generator import NOT_FOUND_MESSAGE, generate_answer


def split_into_chunks(page_texts, filename):
    """Split each page into 800-character chunks with 150-character overlap."""
    chunks = []
    chunk_size = 800
    overlap = 150

    for page_number, page_text in enumerate(page_texts, start=1):
        for start in range(0, len(page_text), chunk_size - overlap):
            end = start + chunk_size
            chunk_text = page_text[start:end].strip()

            if chunk_text:
                chunks.append({
                    "text": chunk_text,
                    "filename": filename,
                    "page_number": page_number,
                })

            # Avoid adding a final chunk containing only the previous overlap.
            if end >= len(page_text):
                break

    return chunks


st.set_page_config(page_title="Document Question Answering", layout="wide")
# Resolve styling relative to the app, regardless of the working directory.
st.markdown(
    "<style>" + Path(__file__).with_name("styles.css").read_text(encoding="utf-8") + "</style>",
    unsafe_allow_html=True,
)
st.markdown(
    """<div class="brand-bar">
        <div class="brand-mark" aria-hidden="true">D</div>
        <div class="brand-name">Document AI</div>
        <div class="brand-label">Your document workspace</div>
    </div>
    <section class="hero">
        <div class="eyebrow">Read less. Understand more.</div>
        <h1>AI-Powered Document Question Answering System</h1>
        <p>Turn your PDF into a conversation. Ask a question, find the relevant
        passages, and get a clear answer with sources you can check.</p>
        <div class="hero-tags"><span>PDF workspace</span>
        <span>Document-grounded answers</span><span>Page citations</span></div>
    </section>""", unsafe_allow_html=True,
)
upload_column, document_column = st.columns([1.1, 1], gap="large")
with upload_column:
    with st.container(border=True, key="upload_panel"):
        st.markdown('<div class="eyebrow">01 / Add your document</div>', unsafe_allow_html=True)
        st.subheader("Document Upload")
        st.caption("Start with a report, guide, paper, or any PDF with selectable text.")
        uploaded_pdf = st.file_uploader(
            "Choose a PDF file", type=["pdf"],
            help="Scanned images cannot be read automatically. Use a PDF with selectable text.",
        )
        st.markdown(
            """<div class="steps">
                <div class="step"><b>1. Upload</b>Choose your PDF</div>
                <div class="step"><b>2. Process</b>Prepare its pages</div>
                <div class="step"><b>3. Ask</b>Explore with citations</div>
            </div>""", unsafe_allow_html=True,
        )

# Identify uploads by both filename and contents, including same-name replacements.
document_id = None
if uploaded_pdf is not None:
    pdf_bytes = uploaded_pdf.getvalue()
    document_id = (uploaded_pdf.name, hashlib.sha256(pdf_bytes).hexdigest())

if "document_index" not in st.session_state:
    st.session_state.document_index = None

# Remove the old index when the PDF changes or the upload is cleared.
previous_index = st.session_state.document_index
if previous_index is not None and previous_index["document_id"] != document_id:
    st.session_state.document_index = None
    if previous_index["collection"] is not None:
        try:
            previous_index["client"].delete_collection(previous_index["collection"].name)
        except Exception:
            st.warning("The previous index could not be cleaned up. It will not be searched.")

with document_column:
    with st.container(border=True, key="document_panel"):
        st.markdown('<div class="eyebrow">02 / Document overview</div>', unsafe_allow_html=True)
        st.subheader("Document Processing")

        if uploaded_pdf is not None:
            # Build once per upload; question submissions reuse this session's index.
            if st.session_state.document_index is None:
                document_index = {
                    "document_id": document_id,
                    "page_texts": [],
                    "page_count": None,
                    "client": None,
                    "collection": None,
                    "chunk_count": 0,
                    "error": None,
                }
                st.session_state.document_index = document_index

                try:
                    with st.spinner("Reading PDF pages..."):
                        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
                            document_index["page_count"] = len(document)
                            for page in document:
                                document_index["page_texts"].append(page.get_text().strip())
                except (RuntimeError, ValueError):
                    document_index["error"] = (
                        "Unable to read this PDF. Please upload a valid, unencrypted PDF file."
                    )

                if document_index["error"] is None:
                    chunks = split_into_chunks(document_index["page_texts"], uploaded_pdf.name)

                    if chunks:
                        try:
                            with st.spinner("Creating the document index..."):
                                client = chromadb.EphemeralClient()
                                # A unique collection keeps separate uploads and sessions apart.
                                # Omitting embedding_function uses ChromaDB's default embeddings.
                                collection = client.create_collection(name=f"pdf_{uuid.uuid4().hex}")
                                document_index["client"] = client
                                document_index["collection"] = collection

                                batch_size = min(100, client.get_max_batch_size())
                                for start in range(0, len(chunks), batch_size):
                                    batch = chunks[start:start + batch_size]
                                    collection.add(
                                        ids=[f"chunk_{start + index}" for index in range(len(batch))],
                                        documents=[chunk["text"] for chunk in batch],
                                        metadatas=[{
                                            "filename": chunk["filename"],
                                            "page_number": chunk["page_number"],
                                        } for chunk in batch],
                                    )

                                document_index["chunk_count"] = len(chunks)
                        except Exception:
                            document_index["error"] = (
                                "Unable to create the document index. Check your connection "
                                "and try uploading the PDF again."
                            )

            document_index = st.session_state.document_index

            # Display cached metadata without regenerating embeddings.
            page_count = document_index.get("page_count", len(document_index["page_texts"]))
            if document_index["error"]:
                status_label, status_class = "Needs attention", "error"
            elif document_index["chunk_count"] > 0:
                status_label, status_class = "Ready for questions", "ready"
            else:
                status_label, status_class = "No readable text", ""
            # Escape uploaded filenames before inserting them into HTML.
            st.markdown(
                f'<span class="status {status_class}">{status_label}</span>'
                f'<div class="document-name">{escape(uploaded_pdf.name)}</div>'
                '<div class="document-details">'
                f'<div class="detail"><small>Pages</small><strong>{page_count if page_count is not None else "Unavailable"}</strong></div>'
                '<div class="detail"><small>File type</small><strong>PDF document</strong></div>'
                '</div>', unsafe_allow_html=True,
            )

            if document_index["error"]:
                st.error(document_index["error"])
            elif document_index["chunk_count"] > 0:
                st.success("Document processing complete. Your PDF is ready for questions.")

            if any(document_index["page_texts"]):
                with st.expander("View extracted document text", expanded=False):
                    for page_number, page_text in enumerate(document_index["page_texts"], start=1):
                        st.markdown(f"**Page {page_number}**")
                        if page_text:
                            st.text(page_text)
                        else:
                            st.write("No readable text found on this page.")
            elif document_index["error"] is None:
                st.info("No readable text found in this PDF. It may contain scanned images.")

        else:
            st.markdown(
                """<div class="empty-document">
                    <div class="document-symbol" aria-hidden="true">PDF</div>
                    <h4>Your document belongs here</h4>
                    <p>Upload a PDF to see its filename, page count, and processing status.</p>
                    <span class="status">Waiting for upload</span>
                </div>""", unsafe_allow_html=True,
            )

document_index = st.session_state.document_index
ready_for_questions = (
    document_index is not None
    and document_index["chunk_count"] > 0
    and document_index["error"] is None
)
with st.container(border=True, key="question_panel"):
    st.markdown('<div class="eyebrow">03 / Explore your document</div>', unsafe_allow_html=True)
    st.subheader("Ask Questions")
    st.caption("Ask a focused question. Your answer will use relevant passages from your PDF.")
    if not ready_for_questions:
        st.caption("Your question workspace becomes available once a readable PDF is processed.")
    with st.form("question_form", border=False):
        question = st.text_input(
            "Your question", key=str(document_id),
            placeholder="What would you like to know about this document?",
            disabled=not ready_for_questions,
        )
        search_submitted = st.form_submit_button(
            "Generate answer", type="primary", disabled=not ready_for_questions,
        )

if search_submitted and ready_for_questions:
    if not question.strip():
        st.info("Please enter a question before generating an answer.")
    else:
        try:
            with st.spinner("Finding relevant document passages..."):
                results = document_index["collection"].query(
                    query_texts=[question.strip()],
                    n_results=min(3, document_index["chunk_count"]),
                    include=["documents", "metadatas"],
                )
            matching_texts = results["documents"][0]
            matching_metadata = results["metadatas"][0]

            # Combine Chroma's parallel text and metadata lists into the
            # chunk dictionaries expected by generate_answer.
            retrieved_chunks = []
            for chunk_text, metadata in zip(matching_texts, matching_metadata):
                if chunk_text and chunk_text.strip():
                    retrieved_chunks.append({
                        "text": chunk_text,
                        "filename": metadata["filename"],
                        "page_number": metadata["page_number"],
                    })
        except Exception:
            st.error("Unable to search the document. Please try again.")
        else:
            st.subheader("AI-Generated Answer")
            if not retrieved_chunks:
                # Do not ask the model to answer without document context.
                st.info(NOT_FOUND_MESSAGE)
            else:
                # This call runs only after an explicit form submission.
                try:
                    with st.spinner("Generating an answer..."):
                        answer_result = generate_answer(question.strip(), retrieved_chunks)

                    if answer_result["error"]:
                        st.warning(answer_result["error"])
                    elif answer_result["answer"] == NOT_FOUND_MESSAGE:
                        st.info(NOT_FOUND_MESSAGE)
                    elif answer_result["answer"]:
                        with st.container(border=True, key="answer_panel"):
                            st.markdown('<div class="eyebrow">Document-grounded response</div>', unsafe_allow_html=True)
                            st.write(answer_result["answer"])
                        # These are the pages supplied as context; the
                        # answer itself cites the pages supporting it.
                        st.subheader("Document Sources")
                        st.caption(
                            "Pages provided as context. The answer cites the pages "
                            "that support its claims."
                        )
                        for source in answer_result["sources"]:
                            st.markdown(
                                '<div class="source-row">'
                                f'<span>{escape(source["filename"])}</span>'
                                f'<strong>Page {source["page_number"]}</strong></div>',
                                unsafe_allow_html=True,
                            )
                    else:
                        st.error("No answer was returned. Please try again.")
                except Exception:
                    st.error("Unable to generate an answer. Please try again.")

                with st.expander("View retrieved document chunks", expanded=False):
                    for rank, chunk in enumerate(retrieved_chunks, start=1):
                        st.text(
                            f"Match {rank} | {chunk['filename']} "
                            f"| Page {chunk['page_number']}"
                        )
                        st.text(chunk["text"])
else:
    st.markdown(
        '<div class="answer-empty"><strong>Answers with evidence.</strong><br>'
        'Your answer and document sources will appear here after you submit a question.</div>',
        unsafe_allow_html=True,
    )

st.markdown(
    '<div class="footer-note">Answers are based on retrieved document passages. '
    'Use the cited pages to verify details.</div>', unsafe_allow_html=True,
)
