"""Vector search against the uploaded resume's FAISS index."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

_HERE = Path(__file__).parent
_VECTOR_DIR = _HERE / "resume_vectors"
_EMBED_MODEL = "text-embedding-3-small"
_EMBED_DIMS = 512

_ROOT = _HERE.parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _load_root_env() -> None:
    """Parse the project-root .env and inject missing keys into os.environ."""
    env_file = _ROOT / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, raw_val = line.partition("=")
        name = name.strip()
        val = raw_val.strip().strip('"').strip("'")
        if name and val and name not in os.environ:
            os.environ[name] = val


_load_root_env()


def _find_index_files() -> tuple[Path, Path] | None:
    """Return (faiss_path, chunks_path) or None if no index exists."""
    if not _VECTOR_DIR.exists():
        return None
    faiss_files = list(_VECTOR_DIR.glob("*.faiss"))
    if not faiss_files:
        return None
    stem = faiss_files[0].stem
    chunks_path = _VECTOR_DIR / f"{stem}_chunks.json"
    return (faiss_files[0], chunks_path) if chunks_path.exists() else None


def resume_fingerprint() -> str:
    """Returns a string that changes whenever the on-disk resume index changes."""
    paths = _find_index_files()
    if paths is None:
        return "no_resume"
    faiss_path, chunks_path = paths
    mtime = max(faiss_path.stat().st_mtime, chunks_path.stat().st_mtime)
    return f"{faiss_path.stem}_{mtime}"


def query_resume(query: str, top_k: int = 5) -> tuple[str | None, str | None]:
    """
    Embed *query* and return (resume_context, error_message).
    resume_context is the top-k most similar resume chunks as a formatted string,
    or None when no index is present.  error_message is set on unexpected failures.
    """
    try:
        import faiss  # local import — avoids cost at module load time
        from openai import OpenAI

        paths = _find_index_files()
        if paths is None:
            return None, None

        faiss_path, chunks_path = paths
        data = json.loads(chunks_path.read_text(encoding="utf-8"))
        chunks: list[str] = data["chunks"]

        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            return None, "OPENAI_API_KEY not set — resume context skipped."

        client = OpenAI(api_key=key)
        response = client.embeddings.create(
            model=_EMBED_MODEL,
            input=[query[:3000]],  # guard against very long JDs
            dimensions=_EMBED_DIMS,
        )
        vec = np.array(response.data[0].embedding, dtype=np.float32)
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec /= norm
        vec = vec.reshape(1, -1)

        index = faiss.read_index(str(faiss_path))
        k = min(top_k, index.ntotal)
        _scores, indices = index.search(vec, k)

        retrieved = [chunks[i] for i in indices[0] if 0 <= i < len(chunks)]
        if not retrieved:
            return None, None

        context = "\n\n".join(
            f"[Resume excerpt {i + 1}]\n{chunk}" for i, chunk in enumerate(retrieved)
        )
        return context, None
    except Exception as exc:
        return None, f"Resume vector search failed: {exc}"
