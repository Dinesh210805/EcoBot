"""
Embed processed JSON documents into ChromaDB collections.
Run: python -m scripts.seed_chromadb

Expected files in data/processed/:
  - disposal_guides.json   → chroma_disposal_collection
  - env_facts.json         → chroma_facts_collection
  - product_kb.json        → chroma_products_collection

Each file is a JSON array of objects: [{id, text, metadata: {...}}, ...]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.db.chroma_db import upsert_documents, collection_count, get_collection
from backend.config import get_settings

settings = get_settings()
PROCESSED_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"

COLLECTION_MAP = {
    "disposal_guides.json": settings.chroma_disposal_collection,
    "env_facts.json": settings.chroma_facts_collection,
    "product_kb.json": settings.chroma_products_collection,
}


def load_and_upsert(filename: str, collection_name: str):
    file_path = PROCESSED_DIR / filename
    if not file_path.exists():
        print(f"[SKIP] {file_path} not found")
        return

    with open(file_path, encoding="utf-8") as f:
        documents = json.load(f)

    if not isinstance(documents, list):
        print(f"[ERROR] {filename} must be a JSON array")
        return

    batch_size = 100
    total = 0
    for i in range(0, len(documents), batch_size):
        batch = documents[i : i + batch_size]
        upsert_documents(collection_name, batch)
        total += len(batch)
        print(f"  Upserted {total}/{len(documents)} documents...")

    count = collection_count(collection_name)
    print(f"[OK] {collection_name}: {count} total documents")


def clear_collection(collection_name: str):
    """Drop and recreate a collection (useful for full re-seed)."""
    from backend.db.chroma_db import get_client, EMBED_FN
    client = get_client()
    try:
        client.delete_collection(collection_name)
        print(f"[CLEAR] Deleted {collection_name}")
    except Exception:
        pass
    client.get_or_create_collection(
        name=collection_name,
        embedding_function=EMBED_FN,
        metadata={"hnsw:space": "cosine"},
    )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--clear", action="store_true", help="Clear collections before seeding")
    args = parser.parse_args()

    print("Seeding ChromaDB...")
    for filename, collection_name in COLLECTION_MAP.items():
        if args.clear:
            clear_collection(collection_name)
        print(f"\nProcessing {filename} → {collection_name}")
        load_and_upsert(filename, collection_name)

    print("\nDone.")
