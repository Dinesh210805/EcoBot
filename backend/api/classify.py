import uuid
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse

from backend.config import get_settings
from backend.middleware.rate_limit import limiter
from backend.models import (
    TextClassifyRequest,
    BatchClassifyRequest,
    ConfirmIdentificationRequest,
    ClassificationResult,
    BatchClassificationResult,
    IdentificationPending,
)
from backend.agent import run_classification, new_session_id
from backend.tools.vision_tool import identify_waste_from_image
from backend.tools.voice_tool import transcribe_audio
from backend.tools.classify_tool import classify_batch

settings = get_settings()
router = APIRouter(prefix="/classify", tags=["classification"])

# In-memory pending store: {pending_id: {identified_item, image_path, input_type}}
# Replace with Redis for multi-instance deployments
_pending: dict[str, dict] = {}


@router.post("/text", response_model=ClassificationResult)
@limiter.limit("30/minute")
async def classify_text(request: Request, body: TextClassifyRequest):
    """
    Classify a waste item from text description.

    - **text**: Item description (e.g., "old newspaper", "dead battery")
    - **session_id**: Optional; creates new session if omitted
    - **location**: City name or 6-digit pincode for facility lookup
    - **include_facilities**: Whether to include nearby facilities in response
    """
    session_id = body.session_id or new_session_id()
    location = body.location if body.include_facilities else None

    result = run_classification(
        item_text=body.text,
        session_id=session_id,
        location=location,
        input_type="text",
    )
    return ClassificationResult(**result)


@router.post("/image", response_model=IdentificationPending)
@limiter.limit("20/minute")
async def classify_image(
    request: Request,
    file: UploadFile = File(...),
    session_id: str = Form(default=None),
    location: str = Form(default=None),
):
    """
    Step 1 of image classification: upload image, get identification + confirmation question.

    Returns a pending_id. Use POST /classify/image/confirm to complete classification.

    - **file**: Image file (JPEG/PNG/WEBP, max 10MB)
    - **session_id**: Optional session ID
    - **location**: City/pincode for facility lookup
    """
    _validate_image(file)
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename).suffix if file.filename else ".jpg"
    file_id = str(uuid.uuid4())
    image_path = upload_dir / f"{file_id}{ext}"

    with open(image_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        identification = identify_waste_from_image(str(image_path))
    except Exception as e:
        image_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"Image analysis failed: {str(e)}")

    pending_id = str(uuid.uuid4())
    _pending[pending_id] = {
        "identified_item": identification["identified_item"],
        "image_path": str(image_path),
        "image_preview_url": f"/uploads/{file_id}{ext}",
        "session_id": session_id or new_session_id(),
        "location": location,
        "input_type": "image",
    }

    return IdentificationPending(
        pending_id=pending_id,
        identified_item=identification["identified_item"],
        confirmation_question=identification.get(
            "clarification_question",
            f"Is this a {identification['identified_item']}?",
        ),
        input_type="image",
        image_preview_url=f"/uploads/{file_id}{ext}",
    )


@router.post("/image/confirm", response_model=ClassificationResult)
@limiter.limit("20/minute")
async def confirm_image(request: Request, body: ConfirmIdentificationRequest):
    """
    Step 2 of image classification: confirm or correct the identified item.

    - **pending_id**: ID from POST /classify/image
    - **confirmed**: true if identification is correct
    - **corrected_item**: Provide if confirmed=false (what the item actually is)
    - **session_id**: Optional; uses session from step 1 if omitted
    - **location**: City/pincode
    """
    pending = _pending.pop(body.pending_id, None)
    if not pending:
        raise HTTPException(status_code=404, detail="Pending identification not found or expired")

    session_id = body.session_id or pending["session_id"]
    item_text = pending["identified_item"] if body.confirmed else (body.corrected_item or pending["identified_item"])

    result = run_classification(
        item_text=item_text,
        session_id=session_id,
        location=body.location or pending["location"],
        input_type="image",
        image_preview_url=pending.get("image_preview_url"),
    )

    # Clean up uploaded file
    Path(pending["image_path"]).unlink(missing_ok=True)
    return ClassificationResult(**result)


@router.post("/voice", response_model=IdentificationPending)
@limiter.limit("20/minute")
async def classify_voice(
    request: Request,
    file: UploadFile = File(...),
    session_id: str = Form(default=None),
    location: str = Form(default=None),
):
    """
    Step 1 of voice classification: upload audio, get transcription + confirmation question.

    Returns a pending_id. Use POST /classify/voice/confirm to complete.

    - **file**: Audio file (MP3/WAV/OGG/M4A/WEBM, max 10MB)
    - **session_id**: Optional session ID
    - **location**: City/pincode
    """
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename).suffix if file.filename else ".mp3"
    file_id = str(uuid.uuid4())
    audio_path = upload_dir / f"{file_id}{ext}"

    with open(audio_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        transcription = transcribe_audio(str(audio_path))
    except Exception as e:
        audio_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"Audio transcription failed: {str(e)}")

    pending_id = str(uuid.uuid4())
    _pending[pending_id] = {
        "identified_item": transcription,
        "audio_path": str(audio_path),
        "session_id": session_id or new_session_id(),
        "location": location,
        "input_type": "voice",
    }

    return IdentificationPending(
        pending_id=pending_id,
        identified_item=transcription,
        confirmation_question=f'I heard: "{transcription}". Is that correct?',
        input_type="voice",
        transcription=transcription,
    )


@router.post("/voice/confirm", response_model=ClassificationResult)
@limiter.limit("20/minute")
async def confirm_voice(request: Request, body: ConfirmIdentificationRequest):
    """
    Step 2 of voice classification: confirm transcription or provide correction.

    - **pending_id**: ID from POST /classify/voice
    - **confirmed**: true if transcription is correct
    - **corrected_item**: Provide if confirmed=false
    """
    pending = _pending.pop(body.pending_id, None)
    if not pending:
        raise HTTPException(status_code=404, detail="Pending identification not found or expired")

    session_id = body.session_id or pending["session_id"]
    item_text = pending["identified_item"] if body.confirmed else (body.corrected_item or pending["identified_item"])

    result = run_classification(
        item_text=item_text,
        session_id=session_id,
        location=body.location or pending["location"],
        input_type="voice",
        voice_transcription=pending["identified_item"],
    )

    audio_path = pending.get("audio_path")
    if audio_path:
        Path(audio_path).unlink(missing_ok=True)

    return ClassificationResult(**result)


@router.post("/batch", response_model=BatchClassificationResult)
@limiter.limit("10/minute")
async def classify_batch_items(request: Request, body: BatchClassifyRequest):
    """
    Classify up to 20 waste items in a single request.

    Returns a summary with hazardous count and per-item results.

    - **items**: List of waste item descriptions (max 20)
    - **session_id**: Optional session ID
    - **location**: City/pincode
    """
    session_id = body.session_id or new_session_id()
    results = classify_batch(body.items)

    items_out = []
    hazardous_count = 0
    for item_text, clf in zip(body.items, results):
        is_haz = clf.get("category") in ("hazardous", "e_waste") or clf.get("hazardous", False)
        if is_haz:
            hazardous_count += 1
        items_out.append({
            "item": item_text,
            "category": clf.get("category", "non_recyclable"),
            "bin_color": clf.get("bin_color", "grey"),
            "bin_label": clf.get("bin_label", "General Waste"),
            "recyclable": clf.get("recyclable", False),
            "confidence": clf.get("confidence", "medium"),
            "reason": clf.get("reason", ""),
            "is_hazardous": is_haz,
        })

    return BatchClassificationResult(
        session_id=session_id,
        items=items_out,
        hazardous_count=hazardous_count,
        total=len(items_out),
    )


def _validate_image(file: UploadFile):
    allowed = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    ext = Path(file.filename).suffix.lower() if file.filename else ""
    if ext not in allowed:
        raise HTTPException(status_code=415, detail=f"Unsupported image format: {ext}")
