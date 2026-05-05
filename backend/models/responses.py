from pydantic import BaseModel
from typing import Optional, Literal


class Facility(BaseModel):
    id: int
    name: str
    address: str
    city: str
    pincode: Optional[str] = None
    accepted_categories: list[str]
    operating_hours: Optional[str] = None
    contact: Optional[str] = None
    verified: bool


class ClassificationResult(BaseModel):
    session_id: str
    item: str
    category: Literal["wet_waste", "dry_waste", "hazardous", "e_waste", "sanitary", "construction", "non_recyclable"]
    bin_color: Literal["green", "blue", "red", "grey", "black"]
    bin_label: str
    recyclable: bool
    confidence: Literal["high", "medium", "low"]
    reason: str
    preparation_steps: list[str]
    safety_notes: Optional[str] = None
    special_facility_required: bool
    environmental_fact: Optional[str] = None
    nearby_facilities: Optional[list[Facility]] = None
    input_type: Literal["text", "image", "voice"]
    image_preview_url: Optional[str] = None
    voice_transcription: Optional[str] = None
    clarification_question: Optional[str] = None


class BatchClassificationItem(BaseModel):
    item: str
    category: str
    bin_color: str
    bin_label: str
    recyclable: bool
    confidence: str
    reason: str
    is_hazardous: bool


class BatchClassificationResult(BaseModel):
    session_id: str
    items: list[BatchClassificationItem]
    hazardous_count: int
    total: int


class IdentificationPending(BaseModel):
    pending_id: str
    identified_item: str
    confirmation_question: str
    input_type: Literal["image", "voice"]
    transcription: Optional[str] = None
    image_preview_url: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    classification: Optional[ClassificationResult] = None


class FacilityListResponse(BaseModel):
    facilities: list[Facility]
    total: int
    city: Optional[str] = None
    category: Optional[str] = None


class WasteCategory(BaseModel):
    key: str
    label: str
    bin_color: str
    description: str
    examples: list[str]


class HealthStatus(BaseModel):
    status: str
    version: str = "1.0.0"
    dependencies: dict[str, str]
    classifier_mode: str
