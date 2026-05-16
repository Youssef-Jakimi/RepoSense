import os
import pickle
import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_model: Optional[object] = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _store_path(persist_dir: str, repo_id: str) -> str:
    return os.path.join(persist_dir, f"{repo_id}.pkl")


class Retriever:
    def __init__(self, embeddings: np.ndarray, documents: list, metadatas: list):
        # normalise once so dot product == cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        self._embeddings = embeddings / norms
        self._documents = documents
        self._metadatas = metadatas

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        model = _get_model()
        qvec = model.encode([query], show_progress_bar=False)[0]
        qvec = qvec / (np.linalg.norm(qvec) or 1)

        scores = self._embeddings @ qvec
        top_idx = np.argsort(scores)[::-1][:top_k]

        out = []
        for i in top_idx:
            meta = self._metadatas[i]
            out.append({
                "content": self._documents[i],
                "path": meta.get("path", ""),
                "language": meta.get("language", ""),
                "start_line": meta.get("start_line", 0),
                "end_line": meta.get("end_line", 0),
                "score": float(scores[i]),
            })
        return out


def embed_chunks(
    repo_id: str,
    chunks: list[dict],
    persist_dir: str = "./chroma_db",
) -> Retriever:
    model = _get_model()
    os.makedirs(persist_dir, exist_ok=True)

    texts = [c["content"] for c in chunks]
    embeddings = model.encode(texts, batch_size=64, show_progress_bar=False)

    metadatas = [
        {
            "path": c["path"],
            "language": c["language"],
            "start_line": c["start_line"],
            "end_line": c["end_line"],
            "chunk_id": c["id"],
        }
        for c in chunks
    ]

    store = {"embeddings": embeddings, "documents": texts, "metadatas": metadatas}
    with open(_store_path(persist_dir, repo_id), "wb") as f:
        pickle.dump(store, f)

    logger.info("Embedded %d chunks for repo '%s'", len(chunks), repo_id)
    return Retriever(embeddings, texts, metadatas)


def get_retriever(repo_id: str, persist_dir: str = "./chroma_db") -> Retriever:
    path = _store_path(persist_dir, repo_id)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"No ingested repo found for repo_id={repo_id}")

    with open(path, "rb") as f:
        store = pickle.load(f)

    return Retriever(store["embeddings"], store["documents"], store["metadatas"])
