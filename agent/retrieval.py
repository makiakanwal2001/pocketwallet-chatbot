"""
Phase 1 — Policy Retrieval
Queries ChromaDB for relevant policy chunks given a customer message.
Embeds the query using local Ollama nomic-embed-text.
Returns top-k chunks with source citations.
"""

import os
import requests
import chromadb

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
EMBED_MODEL = "nomic-embed-text"
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
TOP_K       = 3   # number of chunks to retrieve


def _get_embedding(text: str) -> list[float]:
    resp = requests.post(f"{OLLAMA_HOST}/api/embeddings", json={
        "model":  EMBED_MODEL,
        "prompt": text
    })
    resp.raise_for_status()
    return resp.json()["embedding"]


def _get_collection():
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    return client.get_collection("policy_docs")


def retrieve(query: str, top_k: int = TOP_K) -> list[dict]:
    """
    Embed the query and return top_k matching policy chunks.

    Returns list of:
    {
        "text":       str,   # chunk content
        "source":     str,   # e.g. "fee_policy.md"
        "doc_title":  str,
        "doc_version":str,
        "section":    str,
        "subsection": str,
        "distance":   float  # lower = more similar (cosine)
    }
    """
    embedding  = _get_embedding(query)
    collection = _get_collection()

    results = collection.query(
        query_embeddings=[embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    chunks = []
    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i]
        chunks.append({
            "text":        results["documents"][0][i],
            "source":      meta.get("source", "unknown"),
            "doc_title":   meta.get("doc_title", ""),
            "doc_version": meta.get("doc_version", ""),
            "section":     meta.get("section", ""),
            "subsection":  meta.get("subsection", ""),
            "distance":    round(results["distances"][0][i], 4)
        })

    return chunks


def format_citations(chunks: list[dict]) -> str:
    """
    Format retrieved chunks into a citation string for the LLM prompt.
    Example: [1] Fee Policy v5 > Section 1 > 1.1 Standard Transfer
    """
    lines = []
    for i, chunk in enumerate(chunks, 1):
        citation = (
            f"[{i}] {chunk['doc_title']} > "
            f"{chunk['section']} > {chunk['subsection']}"
        )
        lines.append(f"{citation}\n{chunk['text']}\n")
    return "\n".join(lines)
