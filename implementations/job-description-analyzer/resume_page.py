from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
import faiss
import streamlit as st
from openai import OpenAI

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.python.utils.read_env_key import read_env_key  # noqa: E402

_DOCX_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
_VECTOR_DIR = Path(__file__).parent / "resume_vectors"
_OPENAI_EMBED_MODEL = "text-embedding-3-small"
_EMBED_DIMS = 512  # reduced dimension supported by text-embedding-3-small
_CHUNK_WORDS = 200
_CHUNK_OVERLAP = 40


def _chunk_text(text: str) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    start = 0
    while start < len(words):
        chunks.append(" ".join(words[start : start + _CHUNK_WORDS]))
        start += _CHUNK_WORDS - _CHUNK_OVERLAP
    return [c for c in chunks if c.strip()]


def _embed_chunks(chunks: list[str]) -> np.ndarray:
    key = read_env_key("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set — cannot build vector index.")
    client = OpenAI(api_key=key)
    response = client.embeddings.create(
        model=_OPENAI_EMBED_MODEL,
        input=chunks,
        dimensions=_EMBED_DIMS,
    )
    vecs = [e.embedding for e in sorted(response.data, key=lambda x: x.index)]
    arr = np.array(vecs, dtype=np.float32)
    # L2-normalise so IndexFlatIP gives cosine similarity
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return arr / norms


def _clear_vector_dir() -> None:
    """Remove all files inside _VECTOR_DIR without deleting the directory itself."""
    if _VECTOR_DIR.exists():
        for child in _VECTOR_DIR.iterdir():
            if child.is_file():
                child.unlink()


def _build_faiss_index(resume_text: str, filename: str) -> None:
    _clear_vector_dir()
    _VECTOR_DIR.mkdir(parents=True, exist_ok=True)
    chunks = _chunk_text(resume_text)
    embeddings = _embed_chunks(chunks)
    index = faiss.IndexFlatIP(embeddings.shape[1])  # cosine sim via inner product on normalised vecs
    index.add(embeddings)
    stem = Path(filename).stem
    faiss.write_index(index, str(_VECTOR_DIR / f"{stem}.faiss"))
    (_VECTOR_DIR / f"{stem}_chunks.json").write_text(
        json.dumps({"filename": filename, "chunks": chunks}, indent=2),
        encoding="utf-8",
    )


def extract_resume_text(uploaded_file) -> str:
    if uploaded_file is None:
        return ""
    if not uploaded_file.name.lower().endswith(".docx"):
        return "Unsupported file type. Please upload a .docx Word resume."
    try:
        with zipfile.ZipFile(uploaded_file) as archive:
            xml = archive.read("word/document.xml")
        root = ET.fromstring(xml)
        paragraphs: list[str] = []
        for paragraph in root.findall(".//w:p", _DOCX_NS):
            parts = [node.text for node in paragraph.findall(".//w:t", _DOCX_NS) if node.text]
            text = "".join(parts).strip()
            if text:
                paragraphs.append(text)
        return "\n\n".join(paragraphs).strip()
    except Exception as exc:
        return f"Failed to read resume: {exc}"


def render_resume_page() -> None:
    st.subheader("Resume Viewer")
    uploaded = st.file_uploader("Upload a Word resume (.docx)", type=["docx"])
    resume_text = extract_resume_text(uploaded)

    if not uploaded:
        st.info("Upload a .docx resume to display its contents here.")
        return

    st.caption(f"File: {uploaded.name}")
    st.text_area("Extracted resume text", value=resume_text, height=600, label_visibility="collapsed")

    if resume_text.startswith("Failed to read resume") or resume_text.startswith("Unsupported file type"):
        st.warning(resume_text)
        return

    # Build (or reuse) the FAISS index for this upload.
    # The key encodes both name and size so a different file always triggers a rebuild.
    _index_key = f"_faiss_indexed_{uploaded.name}_{uploaded.size}"
    if not st.session_state.get(_index_key):
        with st.spinner("Building vector index…"):
            try:
                _build_faiss_index(resume_text, uploaded.name)
                st.session_state[_index_key] = True
                st.success(f"Vector index saved to {_VECTOR_DIR.relative_to(Path(__file__).parents[2])}")
            except Exception as exc:
                st.warning(f"Could not build vector index: {exc}")

    st.download_button(
        "Download extracted text",
        data=resume_text.encode("utf-8"),
        file_name=f"{Path(uploaded.name).stem}.txt",
        mime="text/plain",
    )
