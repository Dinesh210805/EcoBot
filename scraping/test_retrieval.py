"""
Sanity-check ChromaDB retrieval with test queries.
Verifies the disposal_guides collection returns relevant results
and correctly reports confidence levels.

Run: python scraping/test_retrieval.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import chromadb
from sentence_transformers import SentenceTransformer

from backend.config import get_settings

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Confidence thresholds (cosine distance — lower = more similar)
HIGH_THRESHOLD = 0.30
MEDIUM_THRESHOLD = 0.60


def distance_to_confidence(distance: float) -> str:
    if distance < HIGH_THRESHOLD:
        return "HIGH"
    if distance < MEDIUM_THRESHOLD:
        return "MEDIUM"
    return "LOW"


TEST_QUERIES = [
    # Common items — should be HIGH confidence
    "plastic water bottle",
    "dead AA battery",
    "old laptop",
    "newspaper",
    "banana peel",
    # Indian-specific items — HIGH confidence if india_specific.json was ingested
    "clay diya",
    "agarbatti ash",
    "steel tiffin box",
    # Edge / ambiguous
    "broken mirror",
]


def run_test_queries(collection: chromadb.Collection, embedder: SentenceTransformer) -> None:
    print(f"{'Query':<35} {'Matched Item':<30} {'Category':<18} {'Bin':<8} {'Dist':>6}  {'Confidence'}")
    print("-" * 115)

    query_embeddings = embedder.encode(TEST_QUERIES).tolist()

    results = collection.query(
        query_embeddings=query_embeddings,
        n_results=1,
        include=["documents", "metadatas", "distances"],
    )

    for i, query in enumerate(TEST_QUERIES):
        distances = results["distances"][i]
        metadatas = results["metadatas"][i]

        if not distances:
            print(f"{query:<35} {'(no results)':<30} {'—':<18} {'—':<8} {'—':>6}  —")
            continue

        dist = distances[0]
        meta = metadatas[0]
        confidence = distance_to_confidence(dist)
        item = meta.get("item", "?")
        category = meta.get("category", "?")
        bin_color = meta.get("bin_color", "?")

        print(
            f"{query:<35} {item:<30} {category:<18} {bin_color:<8} {dist:>6.3f}  {confidence}"
        )


def check_collection_size(client: chromadb.ClientAPI, name: str) -> int:
    try:
        col = client.get_collection(name)
        return col.count()
    except Exception:
        return 0


def main() -> None:
    settings = get_settings()
    db_path = Path(settings.chroma_db_path)

    if not db_path.exists():
        print(f"ChromaDB not found at {db_path}")
        print("Run scraping/ingest_chromadb.py first.")
        sys.exit(1)

    client = chromadb.PersistentClient(path=str(db_path))

    # Collection stats
    print("ChromaDB collection sizes:")
    for name in ("disposal_guides", "env_facts", "product_kb"):
        count = check_collection_size(client, name)
        status = f"{count:,} documents" if count > 0 else "EMPTY or missing"
        print(f"  {name}: {status}")

    dg_count = check_collection_size(client, "disposal_guides")
    if dg_count == 0:
        print("\ndisposal_guides collection is empty — nothing to test.")
        sys.exit(1)

    collection = client.get_collection("disposal_guides")

    print(f"\nLoading embedding model: {EMBEDDING_MODEL}")
    embedder = SentenceTransformer(EMBEDDING_MODEL)

    print(f"\nRunning {len(TEST_QUERIES)} test queries…\n")
    run_test_queries(collection, embedder)

    print("\nConfidence thresholds:")
    print(f"  HIGH   distance < {HIGH_THRESHOLD}")
    print(f"  MEDIUM distance < {MEDIUM_THRESHOLD}")
    print(f"  LOW    distance >= {MEDIUM_THRESHOLD}")


if __name__ == "__main__":
    main()
