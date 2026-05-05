import google.generativeai as genai
from pathlib import Path
from backend.config import get_settings

settings = get_settings()

genai.configure(api_key=settings.gemini_api_key)

_SUPPORTED_MIME = {
    ".mp3": "audio/mp3",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".m4a": "audio/mp4",
    ".webm": "audio/webm",
    ".flac": "audio/flac",
}

_TRANSCRIBE_PROMPT = (
    "Transcribe the spoken audio accurately. "
    "The speaker may use Indian English, Hindi, or regional language mixed with English. "
    "Return ONLY the transcription text, no extra commentary."
)


def transcribe_audio(audio_path: str) -> str:
    """Transcribe audio using Gemini 2.0 Flash. Returns transcription text."""
    suffix = Path(audio_path).suffix.lower()
    mime_type = _SUPPORTED_MIME.get(suffix, "audio/mp3")

    uploaded = genai.upload_file(audio_path, mime_type=mime_type)

    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content([_TRANSCRIBE_PROMPT, uploaded])

    # Clean up uploaded file from Gemini storage
    try:
        genai.delete_file(uploaded.name)
    except Exception:
        pass

    return response.text.strip()
