from pydantic import BaseModel, Field, field_validator
from typing import Optional
import uuid


class TextClassifyRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000, description="Waste item description")
    session_id: Optional[str] = Field(default=None, description="Conversation session ID")
    location: Optional[str] = Field(default=None, description="City name or pincode for facility lookup")
    include_facilities: bool = Field(default=True)

    @field_validator("text")
    @classmethod
    def sanitize_text(cls, v: str) -> str:
        return v.strip()


class BatchClassifyRequest(BaseModel):
    items: list[str] = Field(..., min_length=1, max_length=20, description="List of waste item descriptions")
    session_id: Optional[str] = None
    location: Optional[str] = None

    @field_validator("items")
    @classmethod
    def sanitize_items(cls, v: list[str]) -> list[str]:
        return [item.strip() for item in v if item.strip()]


class ConfirmIdentificationRequest(BaseModel):
    pending_id: str = Field(..., description="ID returned from image/voice endpoint")
    confirmed: bool = Field(...)
    corrected_item: Optional[str] = Field(default=None, description="User correction if confirmed=False")
    session_id: Optional[str] = None
    location: Optional[str] = None
    include_facilities: bool = True


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(..., description="Existing session ID")
    location: Optional[str] = None

    @field_validator("message")
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        return v.strip()


class FacilitySearchRequest(BaseModel):
    city: Optional[str] = None
    pincode: Optional[str] = None
    category: Optional[str] = None
    limit: int = Field(default=5, ge=1, le=20)
