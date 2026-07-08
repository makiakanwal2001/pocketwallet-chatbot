"""
Phase 1 — Policy Embedding Script
Chunks policy markdown files by section and embeds them into ChromaDB
using local Ollama nomic-embed-text model.
"""

import os
import re
import sys
import requests
import chromadb

# ── Config ────────────────────────────────────────────────────────────────────
POLICIES_DIR = os.path.join(os.path.dirname(__file__), "..", "policies")
OLLAMA_HOST  = os.getenv("OLLAMA_HOST", "http://localhost:11434")
EMBED_MODEL  = "nomic-embed-text"
CHROMA_PATH  = os.path.join(os.path.dirname(__file__), "..", "data", "chroma")

# ── Helpers ───────────────────────────────────────────────────────────────────
def __get_embedding(text: str) -> list[float]:
    resp = requests.post(f"{OLLAMA_HOST}/api/embed", json={
        "model":  EMBED_MODEL,
        "input": text
    })
    resp.raise_for_status()
    return resp.json()["embeddings"][0]


def chunk_markdown(text: str, source_file: str) -> list[dict]:
    """
    Split markdown into chunks at each ## heading (subsection level).
    Each chunk carries metadata: source doc, section title, version.
    """
    chunks = []

    # Extract doc-level metadata from first few lines
    lines       = text.strip().split("\n")
    doc_title   = lines[0].lstrip("# ").strip()
    doc_version = "unknown"
    for line in lines[:6]:
        if "Document:" in line:
            doc_version = line.split("Document:")[-1].strip()

    # Split on ## headings (section level)
    sections = re.split(r'\n(?=## )', text)

    for section in sections:
        section = section.strip()
        if not section:
            continue

        first_line    = section.split("\n")[0]
        section_title = first_line.lstrip("# ").strip()

        # Further split on ### headings for finer chunks
        subsections = re.split(r'\n(?=### )', section)
        for sub in subsections:
            sub = sub.strip()
            if len(sub) < 30:
                continue

            first_sub_line   = sub.split("\n")[0]
            subsection_title = first_sub_line.lstrip("# ").strip()

            chunks.append({
                "text": sub,
                "metadata": {
                    "source":      source_file,
                    "doc_title":   doc_title,
                    "doc_version": doc_version,
                    "section":     section_title,
                    "subsection":  subsection_title,
                }
            })

    return chunks


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    # 1. Set up ChromaDB (HTTP client connecting to Docker container)
    client     = chromadb.HttpClient(host="localhost", port=8000)
    collection = client.get_or_create_collection(
        name="policy_docs",
        metadata={"hnsw:space": "cosine"}
    )

    print(f"ChromaDB ready at localhost:8000")
    print(f"Embedding model : {EMBED_MODEL}")
    print(f"Policies dir    : {POLICIES_DIR}\n")

    # 2. Load and process each policy file
    policy_files = [f for f in os.listdir(POLICIES_DIR) if f.endswith(".md")]
    if not policy_files:
        print("ERROR: No .md files found in policies/")
        sys.exit(1)

    total_chunks = 0

    for filename in policy_files:
        filepath = os.path.join(POLICIES_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        chunks = chunk_markdown(text, filename)
        print(f"Processing {filename} -> {len(chunks)} chunks")

        for i, chunk in enumerate(chunks):
            chunk_id = f"{filename}::chunk_{i}"

            # Idempotent — skip if already embedded
            existing = collection.get(ids=[chunk_id])
            if existing["ids"]:
                print(f"  [skip] {chunk_id} already exists")
                continue

            embedding = __get_embedding(chunk["text"])

            collection.add(
                ids        = [chunk_id],
                embeddings = [embedding],
                documents  = [chunk["text"]],
                metadatas  = [chunk["metadata"]]
            )
            print(f"  [ok]   {chunk_id} -- {chunk['metadata']['subsection']}")
            total_chunks += 1

    print(f"\nDone. {total_chunks} chunks embedded into ChromaDB.")
    print(f"Total docs in collection: {collection.count()}")


if __name__ == "__main__":
    main()
