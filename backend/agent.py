"""
EcoBot Agent — orchestrates classification pipeline.
Does NOT use LangChain Agent (too much overhead for structured JSON).
Instead uses a deterministic pipeline: classify → RAG/Exa → response generation.
"""
import uuid
from groq import Groq
from backend.config import get_settings
from backend.prompts import RESPONSE_SYSTEM, CHAT_SYSTEM
from backend.memory import get_session, store_classification
from backend.tools.classify_tool import classify_item
from backend.tools.rag_tool import get_disposal_context, get_environmental_fact, has_rag_coverage
from backend.tools.sql_tool import lookup_bin, find_nearby_facilities
from backend.tools.exa_fallback import search_disposal_info, search_environmental_impact

settings = get_settings()
_groq_client: Groq | None = None


def _groq() -> Groq:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=settings.groq_api_key)
    return _groq_client


def run_classification(
    item_text: str,
    session_id: str,
    location: str | None = None,
    input_type: str = "text",
    image_preview_url: str | None = None,
    voice_transcription: str | None = None,
) -> dict:
    """Full classification pipeline. Returns a dict matching ClassificationResult schema."""
    # 1. Classify
    clf = classify_item(item_text)

    # 2. RAG or Exa fallback for disposal context
    disposal_context = get_disposal_context(item_text, clf.get("category", ""))
    if not disposal_context:
        disposal_context = search_disposal_info(item_text)

    # 3. Environmental fact
    env_fact = get_environmental_fact(item_text, clf.get("category", ""))
    if not env_fact:
        env_fact = search_environmental_impact(item_text)

    # 4. Nearby facilities
    facilities: list[dict] = []
    if location:
        facilities = find_nearby_facilities(location, category=clf.get("category"), limit=3)

    # 5. Generate natural-language response
    natural_response = _generate_response(item_text, clf, disposal_context, env_fact, facilities)

    result = {
        "session_id": session_id,
        "item": item_text,
        "category": clf["category"],
        "bin_color": clf["bin_color"],
        "bin_label": clf["bin_label"],
        "recyclable": clf.get("recyclable", False),
        "confidence": clf.get("confidence", "medium"),
        "reason": clf.get("reason", ""),
        "preparation_steps": clf.get("preparation_steps", []),
        "safety_notes": clf.get("safety_notes"),
        "special_facility_required": clf.get("special_facility_required", False),
        "environmental_fact": env_fact or None,
        "nearby_facilities": facilities or None,
        "input_type": input_type,
        "image_preview_url": image_preview_url,
        "voice_transcription": voice_transcription,
        "clarification_question": None,
        "natural_response": natural_response,
    }

    store_classification(session_id, result)
    session = get_session(session_id)
    session.add_message("assistant", natural_response)
    return result


def run_chat(message: str, session_id: str, location: str | None = None) -> dict:
    """Conversational chat — may or may not involve classification."""
    session = get_session(session_id)
    if location:
        session.location = location

    session.add_message("user", message)
    history = session.get_history_for_llm()

    # Build system context
    system = CHAT_SYSTEM
    if session.last_classification:
        clf = session.last_classification
        system += f"\n\nLast classified item: {clf.get('item')} → {clf.get('category')} ({clf.get('bin_color')} bin)."

    messages = [{"role": "system", "content": system}] + history

    completion = _groq().chat.completions.create(
        model=settings.groq_response_model,
        messages=messages,
        temperature=0.7,
        max_tokens=1024,
    )
    reply = completion.choices[0].message.content.strip()
    session.add_message("assistant", reply)

    # Attempt inline classification if the message looks like an item query
    classification = _try_inline_classification(message, session_id, location)

    return {
        "session_id": session_id,
        "reply": reply,
        "classification": classification,
    }


def _generate_response(
    item: str,
    clf: dict,
    disposal_context: str,
    env_fact: str,
    facilities: list[dict],
) -> str:
    context_parts = []
    if disposal_context:
        context_parts.append(f"Disposal guide: {disposal_context[:600]}")
    if env_fact:
        context_parts.append(f"Environmental fact: {env_fact[:300]}")
    if facilities:
        facility_names = [f["name"] for f in facilities[:2]]
        context_parts.append(f"Nearby facilities: {', '.join(facility_names)}")

    context = "\n".join(context_parts) if context_parts else "No additional context available."

    user_content = (
        f"Item: {item}\n"
        f"Category: {clf.get('category')}\n"
        f"Bin: {clf.get('bin_color')} ({clf.get('bin_label')})\n"
        f"Recyclable: {clf.get('recyclable')}\n"
        f"Steps: {clf.get('preparation_steps')}\n"
        f"Safety: {clf.get('safety_notes')}\n"
        f"Special facility needed: {clf.get('special_facility_required')}\n\n"
        f"Context:\n{context}\n\n"
        "Generate a helpful, friendly disposal response for the user."
    )

    completion = _groq().chat.completions.create(
        model=settings.groq_response_model,
        messages=[
            {"role": "system", "content": RESPONSE_SYSTEM},
            {"role": "user", "content": user_content},
        ],
        temperature=0.7,
        max_tokens=512,
    )
    return completion.choices[0].message.content.strip()


def _try_inline_classification(message: str, session_id: str, location: str | None) -> dict | None:
    """Best-effort: if the message is likely asking about a single item, classify it."""
    trigger_words = ["how to dispose", "where to throw", "which bin", "recycle", "classify", "what bin"]
    msg_lower = message.lower()
    if any(t in msg_lower for t in trigger_words) or len(message.split()) <= 5:
        try:
            clf = classify_item(message)
            facilities = find_nearby_facilities(location, clf.get("category"), limit=2) if location else []
            return {
                "session_id": session_id,
                "item": message,
                **clf,
                "nearby_facilities": facilities or None,
                "input_type": "text",
                "image_preview_url": None,
                "voice_transcription": None,
                "clarification_question": None,
                "environmental_fact": None,
            }
        except Exception:
            return None
    return None


def new_session_id() -> str:
    return str(uuid.uuid4())
