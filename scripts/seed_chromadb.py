"""
Embed processed JSON documents into ChromaDB collections.
Run: python -m scripts.seed_chromadb
     python -m scripts.seed_chromadb --clear

Disposal guide format (disposal_guides.json, india_specific.json):
  [{item, aliases, category, bin_color, bin_label, recyclable,
    reason, preparation_steps, safety_notes, special_facility_required}, ...]

Env facts / product KB format (env_facts.json, product_kb.json):
  [{id, text, metadata: {...}}, ...]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.db.chroma_db import upsert_documents, collection_count, get_collection, get_client, EMBED_FN
from backend.config import get_settings

settings = get_settings()
PROCESSED_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"


# ---------------------------------------------------------------------------
# Transformers — convert each file's native format to {id, text, metadata}
# ---------------------------------------------------------------------------

def _disposal_guide_to_doc(entry: dict, idx: int) -> dict:
    item = entry.get("item", f"item_{idx}")
    reason = entry.get("reason", "")
    steps = entry.get("preparation_steps", [])
    safety = entry.get("safety_notes") or ""
    aliases = ", ".join(entry.get("aliases", []))

    parts = [f"Waste item: {item}."]
    if aliases:
        parts.append(f"Also known as: {aliases}.")
    parts.append(f"Category: {entry.get('category', '')}.")
    if reason:
        parts.append(reason)
    if steps:
        parts.append("How to dispose: " + " ".join(steps))
    if safety:
        parts.append(f"Safety note: {safety}")

    text = " ".join(parts)
    doc_id = f"disposal_{idx:04d}_{item.lower().replace(' ', '_')[:40]}"

    metadata = {
        "item": item,
        "category": entry.get("category", ""),
        "bin_color": entry.get("bin_color", ""),
        "bin_label": entry.get("bin_label", ""),
        "recyclable": str(entry.get("recyclable", False)),
        "special_facility_required": str(entry.get("special_facility_required", False)),
    }
    if entry.get("source_file"):
        metadata["source_file"] = entry["source_file"]

    return {"id": doc_id, "text": text, "metadata": metadata}


def _passthrough_doc(entry: dict, idx: int) -> dict:
    """For env_facts / product_kb which are already in {id, text, metadata} format."""
    if "id" not in entry or "text" not in entry:
        raise ValueError(f"Entry at index {idx} missing required 'id' or 'text' fields")
    return entry


# ---------------------------------------------------------------------------
# Seeding logic
# ---------------------------------------------------------------------------

def seed_disposal_guides() -> None:
    """Merge disposal_guides.json + india_specific.json → disposal_guides collection."""
    collection_name = settings.chroma_disposal_collection
    all_entries: list[dict] = []

    for filename in ("disposal_guides.json", "india_specific.json"):
        path = PROCESSED_DIR / filename
        if not path.exists():
            print(f"  [SKIP] {filename} not found")
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        print(f"  Loaded {len(data)} entries from {filename}")
        all_entries.extend(data)

    if not all_entries:
        print(f"[SKIP] No disposal guide files found — {collection_name} will be empty")
        return

    documents = [_disposal_guide_to_doc(e, i) for i, e in enumerate(all_entries)]

    batch_size = 100
    for i in range(0, len(documents), batch_size):
        upsert_documents(collection_name, documents[i : i + batch_size])
        print(f"  Upserted {min(i + batch_size, len(documents))}/{len(documents)}…")

    print(f"[OK] {collection_name}: {collection_count(collection_name)} total documents")


def seed_passthrough(filename: str, collection_name: str) -> None:
    """Seed files already in {id, text, metadata} format."""
    path = PROCESSED_DIR / filename
    if not path.exists():
        print(f"[SKIP] {filename} not found — {collection_name} will be empty")
        return

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        print(f"[ERROR] {filename} must be a JSON array")
        return

    try:
        documents = [_passthrough_doc(e, i) for i, e in enumerate(data)]
    except ValueError as exc:
        print(f"[ERROR] {filename}: {exc}")
        return

    batch_size = 100
    for i in range(0, len(documents), batch_size):
        upsert_documents(collection_name, documents[i : i + batch_size])
        print(f"  Upserted {min(i + batch_size, len(documents))}/{len(documents)}…")

    print(f"[OK] {collection_name}: {collection_count(collection_name)} total documents")


def clear_all() -> None:
    client = get_client()
    for name in (
        settings.chroma_disposal_collection,
        settings.chroma_facts_collection,
        settings.chroma_products_collection,
    ):
        try:
            client.delete_collection(name)
            print(f"[CLEAR] Deleted {name}")
        except Exception:
            pass
        client.get_or_create_collection(
            name=name,
            embedding_function=EMBED_FN,
            metadata={"hnsw:space": "cosine"},
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--clear", action="store_true", help="Clear collections before seeding")
    args = parser.parse_args()

    if args.clear:
        clear_all()

    print("\nSeeding ChromaDB...")

    print(f"\n→ {settings.chroma_disposal_collection}")
    seed_disposal_guides()

    print(f"\n→ {settings.chroma_facts_collection}")
    seed_passthrough("env_facts.json", settings.chroma_facts_collection)

    print(f"\n→ {settings.chroma_products_collection}")
    seed_passthrough("product_kb.json", settings.chroma_products_collection)

    print("\nDone.")
