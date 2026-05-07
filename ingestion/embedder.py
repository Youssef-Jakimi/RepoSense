import os
import logging
from typing import Optional

import chromadb

logger = logging.getLogger(__name__)

_model: Optional[object] = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


class Retriever:
    def __init__(self, collection):
        self._collection = collection

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        model = _get_model()
        query_embedding = model.encode([query], show_progress_bar=False)[0].tolist()
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        out = []
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for doc, meta, dist in zip(documents, metadatas, distances):
            out.append({
                "content": doc,
                "path": meta.get("path", ""),
                "language": meta.get("language", ""),
                "start_line": meta.get("start_line", 0),
                "end_line": meta.get("end_line", 0),
                "score": 1.0 - dist,
            })

        out.sort(key=lambda x: x["score"], reverse=True)
        return out


def embed_chunks(
    repo_id: str,
    chunks: list[dict],
    persist_dir: str = "./chroma_db",
) -> Retriever:
    """Embed all chunks into ChromaDB collection 'repo_<repo_id>' under persist_dir/<repo_id>/."""
    model = _get_model()
    client = chromadb.PersistentClient(path=os.path.join(persist_dir, repo_id))

    collection_name = f"repo_{repo_id}"
    existing = [c.name for c in client.list_collections()]
    if collection_name in existing:
        client.delete_collection(collection_name)

    collection = client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    batch_size = 64
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c["content"] for c in batch]
        embeddings = model.encode(texts, batch_size=batch_size, show_progress_bar=False)

        collection.add(
            ids=[c["id"] for c in batch],
            documents=texts,
            embeddings=[e.tolist() for e in embeddings],
            metadatas=[
                {
                    "path": c["path"],
                    "language": c["language"],
                    "start_line": c["start_line"],
                    "end_line": c["end_line"],
                    "chunk_id": c["id"],
                }
                for c in batch
            ],
        )
        logger.debug("Embedded batch %d–%d of %d chunks", i, i + len(batch), len(chunks))

    logger.info("Embedded %d chunks into collection '%s'", len(chunks), collection_name)
    return Retriever(collection)


def get_retriever(repo_id: str, persist_dir: str = "./chroma_db") -> Retriever:
    """Load an existing collection without re-embedding."""
    repo_dir = os.path.join(persist_dir, repo_id)
    if not os.path.isdir(repo_dir):
        raise FileNotFoundError(f"No ingested repo found for repo_id={repo_id}")

    client = chromadb.PersistentClient(path=repo_dir)
    collection_name = f"repo_{repo_id}"
    collection = client.get_collection(collection_name)
    return Retriever(collection)
