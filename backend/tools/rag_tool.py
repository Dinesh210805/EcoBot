from backend.db.chroma_db import search_disposal_guides, search_env_facts, search_product_kb


def get_disposal_context(item: str, category: str) -> str:
    """Fetch disposal guide context for the item from ChromaDB."""
    query = f"{item} {category} disposal"
    results = search_disposal_guides(query)
    if not results:
        return ""
    return "\n".join(r["text"] for r in results)


def get_environmental_fact(item: str, category: str) -> str:
    """Fetch an environmental fact relevant to the item."""
    query = f"{item} {category} environmental impact recycling"
    results = search_env_facts(query)
    if not results:
        return ""
    return results[0]["text"]


def get_product_info(item: str) -> str:
    """Fetch product-specific knowledge (e.g., brand-specific recycling info)."""
    results = search_product_kb(item)
    if not results:
        return ""
    return "\n".join(r["text"] for r in results)


def has_rag_coverage(item: str) -> bool:
    """Returns True if ChromaDB has sufficient data for this item."""
    results = search_disposal_guides(item)
    return len(results) > 0
