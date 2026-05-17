"""
Auto-select embedder based on environment.
Uses lite version (API-based) on Vercel, full version (local model) elsewhere.
"""
import os

# Check if running on Vercel
IS_VERCEL = os.getenv("VERCEL") == "1" or os.getenv("VERCEL_ENV") is not None

if IS_VERCEL:
    # Use lightweight API-based embedder for Vercel
    from ingestion.embedder_lite import embed_chunks, get_retriever, Retriever
else:
    # Use full sentence-transformers embedder for local development
    from ingestion.embedder import embed_chunks, get_retriever, Retriever

__all__ = ["embed_chunks", "get_retriever", "Retriever"]

# Made with Bob
