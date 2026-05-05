import json
import httpx
from groq import Groq
from backend.config import get_settings
from backend.prompts import CLASSIFIER_SYSTEM

settings = get_settings()
_groq_client: Groq | None = None


def _groq() -> Groq:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=settings.groq_api_key)
    return _groq_client


def classify_item(item_text: str) -> dict:
    """Classify a waste item using Ollama (primary) or Groq (fallback/serverless)."""
    if settings.use_ollama:
        result = _classify_ollama(item_text)
        if result:
            return result
    return _classify_groq(item_text)


def _classify_ollama(item_text: str) -> dict | None:
    try:
        payload = {
            "model": settings.ollama_model,
            "messages": [
                {"role": "system", "content": CLASSIFIER_SYSTEM},
                {"role": "user", "content": f"Classify this waste item: {item_text}"},
            ],
            "stream": False,
            "options": {"temperature": 0.1},
        }
        resp = httpx.post(
            f"{settings.ollama_base_url}/api/chat",
            json=payload,
            timeout=30.0,
        )
        resp.raise_for_status()
        content = resp.json()["message"]["content"]
        return _parse_classification(content)
    except Exception:
        return None


def _classify_groq(item_text: str) -> dict:
    completion = _groq().chat.completions.create(
        model=settings.groq_classifier_model,
        messages=[
            {"role": "system", "content": CLASSIFIER_SYSTEM},
            {"role": "user", "content": f"Classify this waste item: {item_text}"},
        ],
        temperature=0.1,
        max_tokens=512,
    )
    content = completion.choices[0].message.content
    return _parse_classification(content)


def _parse_classification(content: str) -> dict:
    text = content.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    return json.loads(text)


def classify_batch(items: list[str]) -> list[dict]:
    """Classify multiple items — calls one LLM request per item (parallel-safe)."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=5) as ex:
        results = list(ex.map(classify_item, items))
    return results
