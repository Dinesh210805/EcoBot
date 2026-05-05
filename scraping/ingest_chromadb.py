"""
Ingest processed knowledge base JSON files into ChromaDB.
Creates/replaces 3 collections: disposal_guides, env_facts, product_kb.

Run: python scraping/ingest_chromadb.py
     python scraping/ingest_chromadb.py --collection disposal_guides  # single collection
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import chromadb
from sentence_transformers import SentenceTransformer

from backend.config import get_settings

PROCESSED_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
BATCH_SIZE = 100
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def get_chroma_client(settings) -> chromadb.ClientAPI:
    db_path = Path(settings.chroma_db_path)
    db_path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(db_path))


def build_disposal_doc(guide: dict) -> tuple[str, dict]:
    """Build rich text document + metadata for a disposal guide entry."""
    item = guide.get("item", "")
    aliases = guide.get("aliases", [])
    reason = guide.get("reason", "")
    steps = guide.get("preparation_steps", [])
    safety = guide.get("safety_notes") or ""

    alias_str = f" Also known as: {', '.join(aliases)}." if aliases else ""
    steps_str = " ".join(f"Step {i+1}: {s}" for i, s in enumerate(steps))
    safety_str = f" Safety: {safety}" if safety else ""

    text = f"{item}.{alias_str} Category: {guide.get('category', '')}. Bin: {guide.get('bin_label', '')} ({guide.get('bin_color', '')}). {reason} {steps_str}{safety_str}".strip()

    metadata = {
        "item": item,
        "category": guide.get("category", ""),
        "bin_color": guide.get("bin_color", ""),
        "bin_label": guide.get("bin_label", ""),
        "recyclable": str(guide.get("recyclable", False)),
        "special_facility_required": str(guide.get("special_facility_required", False)),
        "source_file": guide.get("source_file", ""),
    }
    return text, metadata


def ingest_disposal_guides(client: chromadb.ClientAPI, embedder: SentenceTransformer) -> int:
    guides_path = PROCESSED_DIR / "disposal_guides.json"
    india_path = PROCESSED_DIR / "india_specific.json"

    guides: list[dict] = []
    for path in (guides_path, india_path):
        if path.exists():
            with open(path) as f:
                data = json.load(f)
                guides.extend(data)
                print(f"  Loaded {len(data)} entries from {path.name}")
        else:
            print(f"  WARNING: {path.name} not found — skipping")

    if not guides:
        print("  No disposal guides to ingest.")
        return 0

    collection = client.get_or_create_collection(
        name="disposal_guides",
        metadata={"hnsw:space": "cosine"},
    )

    ids, documents, metadatas, embeddings_list = [], [], [], []

    for i, guide in enumerate(guides):
        doc_text, metadata = build_disposal_doc(guide)
        item = guide.get("item", f"item_{i}")
        doc_id = f"dg_{i:05d}_{item[:30].replace(' ', '_').lower()}"

        ids.append(doc_id)
        documents.append(doc_text)
        metadatas.append(metadata)

    # Embed in batches
    print(f"  Embedding {len(documents)} documents…")
    all_embeddings = embedder.encode(documents, batch_size=BATCH_SIZE, show_progress_bar=True).tolist()

    # Upsert in batches
    for batch_start in range(0, len(ids), BATCH_SIZE):
        s, e = batch_start, batch_start + BATCH_SIZE
        collection.upsert(
            ids=ids[s:e],
            documents=documents[s:e],
            metadatas=metadatas[s:e],
            embeddings=all_embeddings[s:e],
        )

    return len(ids)


def ingest_env_facts(client: chromadb.ClientAPI, embedder: SentenceTransformer) -> int:
    path = PROCESSED_DIR / "env_facts.json"
    if not path.exists():
        print(f"  WARNING: env_facts.json not found — skipping")
        return 0

    with open(path) as f:
        facts: list[dict] = json.load(f)

    collection = client.get_or_create_collection(
        name="env_facts",
        metadata={"hnsw:space": "cosine"},
    )

    ids, documents, metadatas = [], [], []

    for i, fact in enumerate(facts):
        text = fact.get("text") or fact.get("fact") or str(fact)
        doc_id = f"ef_{i:05d}"
        ids.append(doc_id)
        documents.append(text)
        metadatas.append({
            "category": fact.get("category", ""),
            "source": fact.get("source", ""),
            "tags": ",".join(fact.get("tags", [])),
        })

    print(f"  Embedding {len(documents)} env facts…")
    all_embeddings = embedder.encode(documents, batch_size=BATCH_SIZE, show_progress_bar=True).tolist()

    for batch_start in range(0, len(ids), BATCH_SIZE):
        s, e = batch_start, batch_start + BATCH_SIZE
        collection.upsert(
            ids=ids[s:e],
            documents=documents[s:e],
            metadatas=metadatas[s:e],
            embeddings=all_embeddings[s:e],
        )

    return len(ids)


def ingest_product_kb(client: chromadb.ClientAPI, embedder: SentenceTransformer) -> int:
    path = PROCESSED_DIR / "product_kb.json"
    if not path.exists():
        print(f"  WARNING: product_kb.json not found — skipping")
        return 0

    with open(path) as f:
        products: list[dict] = json.load(f)

    collection = client.get_or_create_collection(
        name="product_kb",
        metadata={"hnsw:space": "cosine"},
    )

    ids, documents, metadatas = [], [], []

    for i, product in enumerate(products):
        brand = product.get("brand", "")
        model = product.get("model", "")
        category = product.get("category", "")
        disposal = product.get("disposal_notes", "")
        text = f"{brand} {model} — {category}. {disposal}".strip()

        doc_id = f"pk_{i:05d}"
        ids.append(doc_id)
        documents.append(text)
        metadatas.append({
            "brand": brand,
            "model": model,
            "category": category,
        })

    print(f"  Embedding {len(documents)} product KB entries…")
    all_embeddings = embedder.encode(documents, batch_size=BATCH_SIZE, show_progress_bar=True).tolist()

    for batch_start in range(0, len(ids), BATCH_SIZE):
        s, e = batch_start, batch_start + BATCH_SIZE
        collection.upsert(
            ids=ids[s:e],
            documents=documents[s:e],
            metadatas=metadatas[s:e],
            embeddings=all_embeddings[s:e],
        )

    return len(ids)


def print_collection_stats(client: chromadb.ClientAPI) -> None:
    print("\nCollection sizes after ingestion:")
    for name in ("disposal_guides", "env_facts", "product_kb"):
        try:
            col = client.get_collection(name)
            print(f"  {name}: {col.count():,} documents")
        except Exception:
            print(f"  {name}: not found")


def main(only_collection: str | None = None) -> None:
    settings = get_settings()
    client = get_chroma_client(settings)

    print(f"Loading embedding model: {EMBEDDING_MODEL}")
    embedder = SentenceTransformer(EMBEDDING_MODEL)

    total = 0

    if not only_collection or only_collection == "disposal_guides":
        print("\n[1/3] Ingesting disposal guides…")
        n = ingest_disposal_guides(client, embedder)
        print(f"  → {n} documents ingested")
        total += n

    if not only_collection or only_collection == "env_facts":
        print("\n[2/3] Ingesting environmental facts…")
        n = ingest_env_facts(client, embedder)
        print(f"  → {n} documents ingested")
        total += n

    if not only_collection or only_collection == "product_kb":
        print("\n[3/3] Ingesting product knowledge base…")
        n = ingest_product_kb(client, embedder)
        print(f"  → {n} documents ingested")
        total += n

    print(f"\nTotal documents ingested: {total:,}")
    print_collection_stats(client)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--collection",
        choices=["disposal_guides", "env_facts", "product_kb"],
        default=None,
        help="Ingest a single collection (default: all three)",
    )
    args = parser.parse_args()
    main(only_collection=args.collection)
