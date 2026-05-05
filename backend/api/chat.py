from fastapi import APIRouter, Request
from backend.middleware.rate_limit import limiter
from backend.models import ChatRequest, ChatResponse
from backend.agent import run_chat

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
@limiter.limit("40/minute")
async def chat(request: Request, body: ChatRequest):
    """
    Conversational endpoint — maintains context across turns via session_id.

    - **message**: User's message (can be a question, item name, or free text)
    - **session_id**: Must be a valid existing session ID (obtain from any /classify endpoint)
    - **location**: Optional city/pincode; remembered for session if provided once

    The response may include a `classification` object if the message triggered waste classification.
    """
    result = run_chat(
        message=body.message,
        session_id=body.session_id,
        location=body.location,
    )
    return ChatResponse(**result)
