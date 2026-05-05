# EcoBot API Documentation

**Base URL:** `http://localhost:8000/api/v1`  
**Interactive Docs:** `http://localhost:8000/docs` (Swagger UI)  
**Rate Limit:** 60 requests/minute per IP (endpoint-specific limits noted below)

---

## Authentication

No authentication required for v1. Add an `Authorization` header for future private deployments.

---

## Common Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 422 | Validation error (check `detail` field) |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

---

## Endpoints

### 1. `GET /health`

System health check.

**Rate limit:** Unlimited

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "dependencies": {
    "chromadb": "ok (142 docs)",
    "groq": "ok",
    "ollama": "ok",
    "gemini": "configured"
  },
  "classifier_mode": "ollama"
}
```

---

### 2. `POST /classify/text`

Classify a waste item from a text description.

**Rate limit:** 30/minute

**Request:**
```json
{
  "text": "old newspaper",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "location": "Mumbai",
  "include_facilities": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | Yes | Item description (1–1000 chars) |
| `session_id` | string | No | Reuse existing session; creates new if omitted |
| `location` | string | No | City name or 6-digit pincode |
| `include_facilities` | bool | No | Include nearby facilities (default: true) |

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "item": "old newspaper",
  "category": "dry_waste",
  "bin_color": "blue",
  "bin_label": "Dry Recyclable",
  "recyclable": true,
  "confidence": "high",
  "reason": "Newspaper is dry paper waste that can be fully recycled.",
  "preparation_steps": ["Keep dry", "Bundle together", "Remove staples if possible"],
  "safety_notes": null,
  "special_facility_required": false,
  "environmental_fact": "Recycling 1 tonne of newspaper saves 17 trees and 26,000 litres of water.",
  "nearby_facilities": [
    {
      "id": 1,
      "name": "Saahas Zero Waste",
      "address": "No. 31 Rhenius Street",
      "city": "Mumbai",
      "pincode": "400069",
      "accepted_categories": ["dry_waste", "e_waste"],
      "operating_hours": "Mon-Sat 9am-6pm",
      "contact": "+91-80-41255640",
      "verified": true
    }
  ],
  "input_type": "text",
  "image_preview_url": null,
  "voice_transcription": null,
  "clarification_question": null,
  "natural_response": "Great question! Old newspapers go in the 🔵 BLUE (Dry Recyclable) bin..."
}
```

---

### 3. `POST /classify/image`

**Step 1 of 2** — Upload image, receive identification and confirmation question.

**Rate limit:** 20/minute  
**Content-Type:** `multipart/form-data`

**Form fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | File | Yes | Image (JPEG/PNG/WEBP, max 10MB) |
| `session_id` | string | No | Session ID |
| `location` | string | No | City/pincode |

**Response:**
```json
{
  "pending_id": "7f3b4c1d-...",
  "identified_item": "plastic PET water bottle",
  "confirmation_question": "Is this a plastic PET water bottle?",
  "input_type": "image",
  "image_preview_url": "/uploads/abc123.jpg",
  "transcription": null
}
```

> Use `pending_id` in the next step.

---

### 4. `POST /classify/image/confirm`

**Step 2 of 2** — Confirm or correct image identification, get full classification.

**Request:**
```json
{
  "pending_id": "7f3b4c1d-...",
  "confirmed": true,
  "corrected_item": null,
  "session_id": "550e8400-...",
  "location": "Bengaluru",
  "include_facilities": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `pending_id` | string | Yes | From `/classify/image` |
| `confirmed` | bool | Yes | `true` if identification correct |
| `corrected_item` | string | No | Required if `confirmed=false` |
| `session_id` | string | No | Session ID |
| `location` | string | No | City/pincode |

**Response:** Same as `/classify/text` response with `input_type: "image"` and `image_preview_url` set.

---

### 5. `POST /classify/voice`

**Step 1 of 2** — Upload audio, receive transcription and confirmation question.

**Rate limit:** 20/minute  
**Content-Type:** `multipart/form-data`

**Form fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | File | Yes | Audio (MP3/WAV/OGG/M4A/WEBM, max 10MB) |
| `session_id` | string | No | Session ID |
| `location` | string | No | City/pincode |

**Response:**
```json
{
  "pending_id": "9a2e8f5c-...",
  "identified_item": "dead battery from my TV remote",
  "confirmation_question": "I heard: \"dead battery from my TV remote\". Is that correct?",
  "input_type": "voice",
  "transcription": "dead battery from my TV remote",
  "image_preview_url": null
}
```

---

### 6. `POST /classify/voice/confirm`

**Step 2 of 2** — Confirm transcription or provide correction.

Same request/response structure as `/classify/image/confirm` with `input_type: "voice"`.

---

### 7. `POST /classify/batch`

Classify up to 20 waste items in one request.

**Rate limit:** 10/minute

**Request:**
```json
{
  "items": ["old newspaper", "dead battery", "banana peel", "broken phone"],
  "session_id": "550e8400-...",
  "location": "Chennai"
}
```

**Response:**
```json
{
  "session_id": "550e8400-...",
  "items": [
    {
      "item": "old newspaper",
      "category": "dry_waste",
      "bin_color": "blue",
      "bin_label": "Dry Recyclable",
      "recyclable": true,
      "confidence": "high",
      "reason": "Paper waste suitable for recycling.",
      "is_hazardous": false
    },
    {
      "item": "dead battery",
      "category": "hazardous",
      "bin_color": "red",
      "bin_label": "Hazardous Waste",
      "recyclable": false,
      "confidence": "high",
      "reason": "Contains toxic chemicals.",
      "is_hazardous": true
    }
  ],
  "hazardous_count": 2,
  "total": 4
}
```

---

### 8. `POST /chat`

Conversational endpoint — maintains context across multiple turns.

**Rate limit:** 40/minute

**Request:**
```json
{
  "message": "How should I prepare the bottle before recycling?",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "location": "Hyderabad"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | Yes | User message (1–2000 chars) |
| `session_id` | string | Yes | Existing session ID from any /classify endpoint |
| `location` | string | No | City/pincode |

**Response:**
```json
{
  "session_id": "550e8400-...",
  "reply": "For the plastic bottle, rinse it out first, then remove the cap (caps go in a separate bin), and crush it flat to save space. Then drop it in the 🔵 BLUE bin!",
  "classification": null
}
```

> `classification` is non-null when the message triggers waste classification (e.g., "what about a used battery?").

---

### 9. `GET /categories`

Get all 7 waste categories with bin colors and examples.

**Response:**
```json
[
  {
    "key": "wet_waste",
    "label": "Wet Waste",
    "bin_color": "green",
    "description": "Biodegradable organic waste that can be composted.",
    "examples": ["Food scraps", "Vegetable peels", "Cooked food", "Garden trimmings", "Tea leaves"]
  },
  {
    "key": "dry_waste",
    "label": "Dry Recyclable Waste",
    "bin_color": "blue",
    "description": "Clean, dry materials that can be recycled.",
    "examples": ["Newspapers", "Cardboard", "PET bottles", "Aluminium cans", "Glass bottles"]
  }
]
```

---

### 10. `POST /facilities`

Search for nearby recycling/disposal facilities.

**Rate limit:** 30/minute

**Request:**
```json
{
  "city": "Bengaluru",
  "pincode": null,
  "category": "e_waste",
  "limit": 5
}
```

**Response:**
```json
{
  "facilities": [
    {
      "id": 1,
      "name": "E-Parisaraa",
      "address": "No. 235 A Jigani Industrial Area",
      "city": "Bengaluru",
      "pincode": "560105",
      "accepted_categories": ["e_waste"],
      "operating_hours": "Mon-Sat 9am-5pm",
      "contact": "+91-80-27832270",
      "verified": true
    }
  ],
  "total": 1,
  "city": "Bengaluru",
  "category": "e_waste"
}
```

---

## Waste Categories Reference

| Key | Label | Bin Color | Hex |
|-----|-------|-----------|-----|
| `wet_waste` | Wet Waste | green | `#22c55e` |
| `dry_waste` | Dry Recyclable | blue | `#3b82f6` |
| `hazardous` | Hazardous Waste | red | `#ef4444` |
| `e_waste` | E-Waste | red | `#ef4444` |
| `sanitary` | Sanitary Waste | black | `#1f2937` |
| `construction` | C&D Waste | grey | `#6b7280` |
| `non_recyclable` | Non-Recyclable | grey | `#6b7280` |

---

## Typical UI Flow

### Text classification
```
User types item → POST /classify/text → Show result card with bin color
→ User asks follow-up → POST /chat (same session_id)
```

### Image classification
```
User uploads photo → POST /classify/image → Show preview + "Is this X?" confirm dialog
→ User taps Yes/No → POST /classify/image/confirm → Show result card
```

### Voice classification
```
User records audio → POST /classify/voice → Show transcription + confirm prompt
→ User confirms → POST /classify/voice/confirm → Show result card
```

### Batch (inventory scan)
```
User provides list → POST /classify/batch → Show table with hazard summary
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Groq API key (response generation + vision) |
| `GEMINI_API_KEY` | Yes | Google Gemini API key (voice transcription) |
| `EXA_API_KEY` | Yes | Exa.ai API key (fallback search) |
| `CLASSIFIER_MODE` | No | `ollama` (default) or `groq` |
| `OLLAMA_BASE_URL` | No | Ollama URL (default: http://localhost:11434) |
| `CORS_ORIGINS` | No | Comma-separated allowed origins |
| `API_PORT` | No | Server port (default: 8000) |

---

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and fill env vars
cp .env.example .env

# Initialize database
python -m scripts.init_db

# Start server
uvicorn backend.main:app --reload --port 8000

# Run tests
pytest tests/ -v
```

## Docker

```bash
docker compose up --build
```

The Swagger docs at `http://localhost:8000/docs` are the fastest way to explore and test all endpoints.
