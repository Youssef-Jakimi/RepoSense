"""
End-to-end smoke test for the RepoSense ingestion pipeline.

Usage:
    python scripts/smoke_ingest.py
    python -m scripts.smoke_ingest
"""

import os
import sys
import traceback

# Ensure project root is on sys.path regardless of invocation style.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SMOKE_REPO_URL = "https://github.com/psf/requests-html"
_FALLBACK_URL  = "https://github.com/octocat/Hello-World"


def main() -> None:
    from dotenv import load_dotenv
    load_dotenv()

    from ingestion import github_loader, chunker, embedder

    github_token = os.environ.get("GITHUB_TOKEN") or None
    persist_dir  = os.environ.get("CHROMA_PERSIST_DIR", "./chroma_db")

    # --- 1. Load repo (fall back on any exception) ---
    print(f"Loading repo: {SMOKE_REPO_URL}")
    try:
        loader_output = github_loader.load_repo(SMOKE_REPO_URL, github_token=github_token)
    except Exception as exc:
        print(f"Primary repo failed ({exc!r}), falling back to: {_FALLBACK_URL}")
        loader_output = github_loader.load_repo(_FALLBACK_URL, github_token=github_token)

    repo_id    = loader_output["repo_id"]
    files      = loader_output["files"]
    file_count = len(files)

    print(f"Repo ID   : {repo_id}")
    print(f"Files     : {file_count}")

    # --- 2. Chunk ---
    print("Chunking files...")
    chunks      = chunker.chunk_files(files)
    chunk_count = len(chunks)
    print(f"Chunks    : {chunk_count}")

    # --- 3. Embed into ChromaDB ---
    print("Embedding chunks into ChromaDB...")
    retriever = embedder.embed_chunks(repo_id, chunks, persist_dir=persist_dir)

    chroma_path = os.path.join(persist_dir, repo_id)
    chroma_ok   = os.path.isdir(chroma_path)
    print(f"ChromaDB  : {chroma_path}  (exists={chroma_ok})")

    # --- 4. Retrieve ---
    query = "how does the main entry point work?"
    print(f'Searching : "{query}"')
    results = retriever.search(query, top_k=3)

    if results:
        top = results[0]
        print(f"\nTop result:")
        print(f"  path    : {top['path']}")
        print(f"  score   : {top['score']:.4f}")
        print(f"  content : {top['content'][:200]!r}")
    else:
        print("\nNo results returned (collection may be empty).")

    print("\nSmoke test PASSED.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
    sys.exit(0)
