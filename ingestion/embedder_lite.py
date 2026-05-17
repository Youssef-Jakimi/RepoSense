"""
Lightweight embedder for Vercel deployment.
Uses IBM watsonx.ai embeddings API instead of local sentence-transformers.
"""
import os
import pickle
import logging
from typing import Optional
import httpx
import numpy as np

logger = logging.getLogger(__name__)


def _store_path(persist_dir: str, repo_id: str) -> str:
    return os.path.join(persist_dir, f"{repo_id}.pkl")


def _get_watsonx_embeddings(texts: list[str]) -> np.ndarray:
    """Get embeddings from IBM watsonx.ai API"""
    api_key = os.getenv("WATSONX_API_KEY")
    project_id = os.getenv("WATSONX_PROJECT_ID")
    
    if not api_key or not project_id:
        raise ValueError("WATSONX_API_KEY and WATSONX_PROJECT_ID must be set")
    
    url = "https://us-south.ml.cloud.ibm.com/ml/v1/text/embeddings?version=2023-05-29"
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # Process in batches to avoid API limits
    batch_size = 10
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        payload = {
            "inputs": batch,
            "model_id": "ibm/slate-125m-english-rtrvr",
            "project_id": project_id
        }
        
        try:
            response = httpx.post(url, headers=headers, json=payload, timeout=30.0)
            response.raise_for_status()
            result = response.json()
            
            # Extract embeddings from response
            embeddings = [r["embedding"] for r in result["results"]]
            all_embeddings.extend(embeddings)
            
        except Exception as e:
            logger.error(f"Error getting embeddings for batch {i}: {e}")
            # Fallback: use zero vectors
            all_embeddings.extend([[0.0] * 384 for _ in batch])
    
    return np.array(all_embeddings, dtype=np.float32)


class Retriever:
    def __init__(self, embeddings: np.ndarray, documents: list, metadatas: list):
        self._documents = documents
        self._metadatas = metadatas
        if len(documents) == 0:
            self._embeddings = np.empty((0, 1), dtype=np.float32)
            return
        # normalise once so dot product == cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        self._embeddings = embeddings / norms

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        if not self._documents:
            return []
        
        qvec = _get_watsonx_embeddings([query])[0]
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
    os.makedirs(persist_dir, exist_ok=True)

    texts = [c["content"] for c in chunks]
    embeddings = _get_watsonx_embeddings(texts)

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

# Made with Bob
