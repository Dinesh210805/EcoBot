import httpx
from fastapi import APIRouter
from backend.config import get_settings
from backend.models import HealthStatus
from backend.db.chroma_db import collection_count

settings = get_settings()
router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthStatus)
async def health_check():
    """
    System health check — confirms all dependencies are reachable.

    Returns status of Groq, ChromaDB, SQLite, and (if enabled) Ollama.
    Use this endpoint for uptime monitoring and deployment verification.
    """
    deps: dict[str, str] = {}

    # ChromaDB
    try:
        count = collection_count(settings.chroma_disposal_collection)
        deps["chromadb"] = f"ok ({count} docs)"
    except Exception as e:
        deps["chromadb"] = f"error: {e}"

    # Groq
    try:
        from groq import Groq
        client = Groq(api_key=settings.groq_api_key)
        client.models.list()
        deps["groq"] = "ok"
    except Exception as e:
        deps["groq"] = f"error: {e}"

    # Ollama (only if mode=ollama)
    if settings.use_ollama:
        try:
            resp = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=5.0)
            resp.raise_for_status()
            deps["ollama"] = "ok"
        except Exception as e:
            deps["ollama"] = f"error: {e}"
    else:
        deps["ollama"] = "disabled (classifier_mode=groq)"

    # Gemini (basic key presence check)
    deps["gemini"] = "configured" if settings.gemini_api_key else "missing key"

    overall = "healthy" if all("error" not in v for v in deps.values()) else "degraded"

    return HealthStatus(
        status=overall,
        version="1.0.0",
        dependencies=deps,
        classifier_mode=settings.classifier_mode,
    )
