from exa_py import Exa
from backend.config import get_settings

settings = get_settings()
_exa_client: Exa | None = None


def _exa() -> Exa:
    global _exa_client
    if _exa_client is None:
        _exa_client = Exa(api_key=settings.exa_api_key)
    return _exa_client


def search_disposal_info(item: str) -> str:
    """
    Search Exa.ai for disposal information when ChromaDB has no results.
    Returns combined text from top results, empty string if search fails.
    """
    try:
        query = f"how to dispose {item} waste India recycling bin"
        results = _exa().search_and_contents(
            query,
            num_results=settings.exa_search_num_results,
            use_autoprompt=True,
            text={"max_characters": 800},
        )
        snippets = []
        for r in results.results:
            if r.text:
                snippets.append(r.text.strip())
        return "\n\n".join(snippets)
    except Exception:
        return ""


def search_environmental_impact(item: str) -> str:
    """Search for environmental impact facts about the item."""
    try:
        query = f"{item} environmental impact pollution recycling statistics"
        results = _exa().search_and_contents(
            query,
            num_results=2,
            use_autoprompt=True,
            text={"max_characters": 500},
        )
        snippets = [r.text.strip() for r in results.results if r.text]
        return " ".join(snippets[:2])
    except Exception:
        return ""
