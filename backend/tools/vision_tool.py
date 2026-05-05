import base64
import json
from pathlib import Path
from groq import Groq
from backend.config import get_settings
from backend.prompts import VISION_IDENTIFY_SYSTEM

settings = get_settings()
_groq_client: Groq | None = None


def _groq() -> Groq:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=settings.groq_api_key)
    return _groq_client


def identify_waste_from_image(image_path: str) -> dict:
    """Send image to LLaMA 4 Scout via Groq. Returns {identified_item, confidence, clarification_question}."""
    image_data = _encode_image(image_path)
    mime_type = _get_mime_type(image_path)

    completion = _groq().chat.completions.create(
        model=settings.groq_vision_model,
        messages=[
            {"role": "system", "content": VISION_IDENTIFY_SYSTEM},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_data}",
                        },
                    },
                    {
                        "type": "text",
                        "text": "What waste item is in this image? Identify it precisely.",
                    },
                ],
            },
        ],
        temperature=0.1,
        max_tokens=256,
    )

    content = completion.choices[0].message.content.strip()
    return _parse_json(content)


def _encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _get_mime_type(image_path: str) -> str:
    suffix = Path(image_path).suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    return mime_map.get(suffix, "image/jpeg")


def _parse_json(content: str) -> dict:
    text = content.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    return json.loads(text)
