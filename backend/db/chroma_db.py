import json
import os
from typing import Optional
from pathlib import Path

# Silence chromadb telemetry error prints
import logging
logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from backend.config import get_settings

settings = get_settings()

_client: Optional[chromadb.PersistentClient] = None

EMBED_FN = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)


def get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        Path(settings.chroma_db_path).mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=settings.chroma_db_path,
            settings=Settings(anonymized_telemetry=False)
        )
    return _client


def get_collection(name: str) -> chromadb.Collection:
    return get_client().get_or_create_collection(
        name=name,
        embedding_function=EMBED_FN,
        metadata={"hnsw:space": "cosine"},
    )


def search_disposal_guides(query: str, top_k: int = None) -> list[dict]:
    k = top_k or settings.rag_top_k
    col = get_collection(settings.chroma_disposal_collection)
    results = col.query(query_texts=[query], n_results=k, include=["documents", "metadatas", "distances"])
    return _filter_by_threshold(results)


def search_env_facts(query: str, top_k: int = None) -> list[dict]:
    k = top_k or settings.rag_top_k
    col = get_collection(settings.chroma_facts_collection)
    results = col.query(query_texts=[query], n_results=k, include=["documents", "metadatas", "distances"])
    return _filter_by_threshold(results)


def search_product_kb(query: str, top_k: int = None) -> list[dict]:
    k = top_k or settings.rag_top_k
    col = get_collection(settings.chroma_products_collection)
    results = col.query(query_texts=[query], n_results=k, include=["documents", "metadatas", "distances"])
    return _filter_by_threshold(results)


def _filter_by_threshold(results: dict) -> list[dict]:
    threshold = settings.rag_similarity_threshold
    out = []
    if not results["documents"] or not results["documents"][0]:
        return out
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        # cosine distance → similarity: 1 - distance
        similarity = 1.0 - dist
        if similarity >= threshold:
            out.append({"text": doc, "metadata": meta, "similarity": round(similarity, 4)})
    return out


def upsert_documents(collection_name: str, documents: list[dict]):
    """documents: list of {id, text, metadata}"""
    col = get_collection(collection_name)
    col.upsert(
        ids=[d["id"] for d in documents],
        documents=[d["text"] for d in documents],
        metadatas=[d.get("metadata", {}) for d in documents],
    )


def collection_count(collection_name: str) -> int:
    return get_collection(collection_name).count()
