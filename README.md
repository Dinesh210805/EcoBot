# EcoBot — AI-Powered Waste Classification & Recycling Assistant

EcoBot is a production-ready multimodal AI backend that classifies household and industrial waste for Indian cities. It accepts **text, image, or voice** input and returns bin color, disposal instructions, preparation steps, environmental facts, and nearby recycling facility locations — all in a single structured JSON response.

Built on FastAPI with a deterministic pipeline (no LangChain agent overhead), it uses a fine-tuned LLaMA 3 8B model for classification and LLaMA 3 70B on Groq for natural language responses.

---

## What EcoBot Does

A user describes, photographs, or speaks about a waste item. EcoBot:

1. **Identifies** what the item is (for images/voice)
2. **Classifies** it into one of 7 waste categories
3. **Returns** the correct bin color, disposal steps, safety notes, and an environmental fact
4. **Finds** nearby recycling/disposal facilities by city or pincode
5. **Continues** a conversation across multiple turns with session memory

---

## Waste Categories

| Category | Bin Color | Examples |
|---|---|---|
| `wet_waste` | 🟢 Green | Food scraps, vegetable peels, garden waste |
| `dry_waste` | 🔵 Blue | Newspapers, cardboard, PET bottles, cans |
| `hazardous` | 🔴 Red | Batteries, paint, pesticides, medicines |
| `e_waste` | 🔴 Red | Phones, laptops, chargers, ink cartridges |
| `sanitary` | ⚫ Black | Sanitary pads, diapers, bandages |
| `construction` | ⬜ Grey | Bricks, tiles, cement debris |
| `non_recyclable` | ⬜ Grey | Thermocol, soiled wrappers, broken crockery |

---

## Architecture

```
User Input (text / image / voice)
         │
         ▼
   Input Processor
   ├── Text   → used directly
   ├── Image  → LLaMA 4 Scout (Groq) → identified item name
   └── Voice  → Gemini 2.0 Flash     → transcribed text
         │
         ▼
   Classification Pipeline  (deterministic, not agent-based)
   ├── classify_tool    → Fine-tuned LLaMA 3 8B via Ollama
   │                      (fallback: LLaMA 3 70B via Groq)
   ├── rag_tool         → ChromaDB  (disposal guides, env facts, product KB)
   │                      ↓ if similarity < 0.70
   ├── exa_fallback     → Exa.ai live search
   ├── sql_tool         → SQLite (bin colors, facility lookup)
   └── response_gen     → LLaMA 3 70B via Groq (final natural response)
         │
         ▼
   Session Memory  (per session_id, in-memory, LRU eviction at 500 sessions)
         │
         ▼
   FastAPI REST  →  Structured JSON response
```

### Why a deterministic pipeline instead of a LangChain Agent?

Classification needs consistent JSON output with exact field names. An autonomous agent introduces non-determinism in tool selection and output format. The deterministic pipeline runs the same steps in the same order every time — classify → RAG → Exa fallback → response generation — which is faster, cheaper, and produces reliable structured output.

---

## Tech Stack

| Layer | Technology |
|---|---|
| API Framework | FastAPI 0.115 + Uvicorn |
| Classification | Fine-tuned LLaMA 3 8B (Ollama) / LLaMA 3 70B (Groq fallback) |
| Vision | LLaMA 4 Scout 17B via Groq (native multimodal) |
| Voice | Gemini 2.0 Flash via Google File API |
| Response Generation | LLaMA 3 70B-8192 via Groq |
| RAG / Vector DB | ChromaDB + all-MiniLM-L6-v2 embeddings |
| Fallback Search | Exa.ai |
| Relational DB | SQLite (bin colors, facilities, waste items) |
| Rate Limiting | slowapi (per-endpoint limits) |
| Session Memory | In-memory dict with LRU eviction |
| Config | pydantic-settings |
| Fine-Tuning | QLoRA (rank=16, alpha=32) on T4 GPU |

---

## Project Structure

```
EcoBot/
├── CLAUDE.md                    # Project guide for AI-assisted development
├── .env.example                 # All environment variables (copy → .env)
├── requirements.txt
├── Dockerfile                   # Multi-stage build (pre-downloads embedding model)
├── docker-compose.yml           # EcoBot + Ollama services
│
├── backend/
│   ├── main.py                  # FastAPI app, middleware, routers
│   ├── config.py                # Settings via pydantic-settings
│   ├── agent.py                 # Core orchestration pipeline
│   ├── memory.py                # Session memory (thread-safe, LRU eviction)
│   ├── prompts.py               # All system prompts (classifier, vision, chat, batch)
│   │
│   ├── models/
│   │   ├── requests.py          # Pydantic request schemas
│   │   └── responses.py         # Pydantic response schemas
│   │
│   ├── db/
│   │   ├── sqlite_db.py         # SQLite: bin colors, facilities, waste items
│   │   └── chroma_db.py         # ChromaDB: vector search across 3 collections
│   │
│   ├── tools/
│   │   ├── classify_tool.py     # Ollama → Groq fallback classification
│   │   ├── vision_tool.py       # LLaMA 4 Scout image identification
│   │   ├── voice_tool.py        # Gemini 2.0 Flash transcription
│   │   ├── rag_tool.py          # ChromaDB retrieval (disposal, facts, products)
│   │   ├── sql_tool.py          # SQLite bin lookup + facility finder
│   │   └── exa_fallback.py      # Exa.ai fallback when RAG coverage is low
│   │
│   ├── api/
│   │   ├── classify.py          # /classify/text, /image, /voice, /batch endpoints
│   │   ├── chat.py              # /chat endpoint (multi-turn conversation)
│   │   ├── facilities.py        # /categories, /facilities endpoints
│   │   └── health.py            # /health dependency check
│   │
│   └── middleware/
│       └── rate_limit.py        # slowapi limiter instance
│
├── scripts/
│   ├── init_db.py               # Create + seed SQLite from CSV files
│   └── seed_chromadb.py         # Embed processed JSON into ChromaDB
│
├── scraping/
│   ├── crawl_earth911.py        # Crawl4AI scraper for Earth911 guides
│   ├── crawl_cpcb.py            # Firecrawl PDF parser for CPCB documents
│   ├── convert_to_json.py       # Groq distillation: raw markdown → structured JSON
│   └── augment_dataset.py       # Generate Alpaca training pairs from waste_items.csv
│
├── data/
│   ├── facilities.csv           # 15 real Indian recycling facilities (seed data)
│   ├── waste_items.csv          # 30 waste items with full metadata (seed data)
│   ├── raw/                     # Scraped markdown and PDFs
│   ├── processed/               # Structured JSON for ChromaDB ingestion
│   └── finetuning/              # train.jsonl + test.jsonl
│
├── embeddings/
│   └── chroma_db/               # ChromaDB persistent storage
│
├── fine_tuning/
│   └── ecobot_finetune.ipynb    # QLoRA training notebook (Colab / Kaggle)
│
├── tests/
│   └── test_classification.py   # Integration tests (pytest)
│
└── docs/
    └── API.md                   # Complete endpoint reference
```

---

## Quickstart

### Prerequisites

- Python 3.11+
- API keys: [Groq](https://console.groq.com), [Google AI Studio](https://aistudio.google.com), [Exa](https://exa.ai)
- (Optional for local classifier) [Ollama](https://ollama.ai) running with the fine-tuned model

### 1. Install

```bash
git clone <repo-url>
cd EcoBot

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` and fill in your API keys:

```env
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AIza...
EXA_API_KEY=exa-...

# Use "groq" if you don't have Ollama set up yet
CLASSIFIER_MODE=groq
```

### 3. Initialize the database

```bash
python -m scripts.init_db
```

This creates `data/ecobot.db` and seeds it with 15 real Indian facilities and 30 waste items.

### 4. (Optional) Seed ChromaDB

If you have processed knowledge base files in `data/processed/`:

```bash
python -m scripts.seed_chromadb
```

Without this step, the API falls back to Exa.ai for disposal context — fully functional, just uses live search instead of local RAG.

### 5. Start the server

```bash
uvicorn backend.main:app --reload --port 8000
```

- API: `http://localhost:8000/api/v1`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Running with Docker

The Docker setup includes both EcoBot and an Ollama sidecar for the local fine-tuned model.

```bash
# Copy and fill your .env first
cp .env.example .env

docker compose up --build
```

After the containers start, register your fine-tuned model with Ollama:

```bash
docker exec -it ecobot-ollama-1 ollama create ecobot-classifier -f /path/to/Modelfile
```

If you haven't fine-tuned yet, set `CLASSIFIER_MODE=groq` in your `.env` and omit the Ollama step.

---

## API Overview

All endpoints are prefixed with `/api/v1`. Full documentation: [`docs/API.md`](docs/API.md)

| Method | Endpoint | Description | Rate Limit |
|---|---|---|---|
| `GET` | `/health` | Dependency check (ChromaDB, Groq, Ollama, Gemini) | Unlimited |
| `POST` | `/classify/text` | Classify a waste item from text | 30/min |
| `POST` | `/classify/image` | Step 1: Upload image, get identification | 20/min |
| `POST` | `/classify/image/confirm` | Step 2: Confirm identification, get classification | 20/min |
| `POST` | `/classify/voice` | Step 1: Upload audio, get transcription | 20/min |
| `POST` | `/classify/voice/confirm` | Step 2: Confirm transcription, get classification | 20/min |
| `POST` | `/classify/batch` | Classify up to 20 items at once | 10/min |
| `POST` | `/chat` | Multi-turn conversation with session context | 40/min |
| `GET` | `/categories` | All 7 waste categories with examples | Unlimited |
| `POST` | `/facilities` | Search recycling facilities by city or pincode | 30/min |

### Quick examples

**Classify text:**
```bash
curl -X POST http://localhost:8000/api/v1/classify/text \
  -H "Content-Type: application/json" \
  -d '{"text": "old newspaper", "location": "Mumbai"}'
```

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
  "environmental_fact": "Recycling 1 tonne of newspaper saves 17 trees and 26,000 litres of water.",
  "nearby_facilities": [...],
  "natural_response": "Great question! Old newspapers go in the 🔵 BLUE (Dry Recyclable) bin..."
}
```

**Image classification (2 steps):**
```bash
# Step 1 — upload image
curl -X POST http://localhost:8000/api/v1/classify/image \
  -F "file=@water_bottle.jpg" -F "location=Bengaluru"

# Step 2 — confirm identification
curl -X POST http://localhost:8000/api/v1/classify/image/confirm \
  -H "Content-Type: application/json" \
  -d '{"pending_id": "<id from step 1>", "confirmed": true, "location": "Bengaluru"}'
```

**Batch classification:**
```bash
curl -X POST http://localhost:8000/api/v1/classify/batch \
  -H "Content-Type: application/json" \
  -d '{"items": ["newspaper", "dead battery", "banana peel", "broken phone"], "location": "Chennai"}'
```

**Multi-turn chat:**
```bash
# First classify something to get a session_id
# Then continue the conversation
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How should I prepare the bottle before recycling?", "session_id": "<your-session-id>"}'
```

---

## Input Modalities

### Text
Direct item description in English, Hindi-English mix, or common abbreviations. 1–1000 characters.

### Image (2-step flow)
1. `POST /classify/image` with `multipart/form-data` — EcoBot uses LLaMA 4 Scout to identify the item and returns a confirmation question
2. `POST /classify/image/confirm` — User confirms or corrects the identification; EcoBot returns full classification

Supported formats: JPEG, PNG, WEBP, GIF (max 10 MB)

### Voice (2-step flow)
1. `POST /classify/voice` — Gemini 2.0 Flash transcribes the audio (tuned for Indian English and Hindi code-switching)
2. `POST /classify/voice/confirm` — User confirms the transcription; EcoBot returns full classification

Supported formats: MP3, WAV, OGG, M4A, WEBM, FLAC (max 10 MB)

---

## Fine-Tuning the Classifier

The classifier uses a LLaMA 3 8B model fine-tuned with QLoRA on Indian waste classification data. Training runs free on a T4 GPU (Google Colab or Kaggle).

### Step 1 — Generate training data

```bash
python scraping/augment_dataset.py \
  --output data/finetuning/train_augmented.jsonl \
  --per-item 5
```

This reads `data/waste_items.csv` and generates:
- One entry per canonical item name
- One entry per alias (e.g., "mobile" for "smartphone")
- 5 LLM-generated variations per item (casual language, Indian English, misspellings)

### Step 2 — Train in Colab/Kaggle

Open `fine_tuning/ecobot_finetune.ipynb`:

1. Upload `train_augmented.jsonl` to `/content/data/`
2. Set your HuggingFace token in Colab Secrets (`HF_TOKEN`)
3. Run all cells in order

The notebook:
- Loads `meta-llama/Meta-Llama-3-8B-Instruct` in 4-bit (NF4 quantization)
- Applies LoRA adapters (rank=16, alpha=32) to all attention + MLP layers
- Trains for 3 epochs with cosine LR schedule, effective batch size 16
- Merges adapters into base model and converts to GGUF (Q4_K_M, ~4.5 GB)
- Creates an Ollama `Modelfile` with `temperature=0.1`

### Step 3 — Register with Ollama

```bash
# Download the GGUF and Modelfile from Colab, then:
ollama create ecobot-classifier -f Modelfile
ollama run ecobot-classifier "Classify this waste item: old battery"
```

Set `CLASSIFIER_MODE=ollama` in your `.env` to use the fine-tuned model.

---

## Knowledge Base Setup

The RAG system uses three ChromaDB collections. You can populate them in two ways:

### Option A — Bring your own JSON (recommended)

Place structured JSON files in `data/processed/` with the expected format:

```json
[
  {
    "id": "unique-id",
    "text": "Dispose of AA batteries at designated drop-off points...",
    "metadata": {"category": "hazardous", "item": "battery"}
  }
]
```

Then seed ChromaDB:

```bash
python -m scripts.seed_chromadb --clear
```

### Option B — Distill from raw scraped markdown

If you have raw markdown or text files in `data/raw/`, use the Groq distillation script to convert them to the structured JSON format above:

```bash
python scraping/convert_to_json.py \
  --input data/raw/earth911 \
  --output data/processed/disposal_guides.json
```

Then run `seed_chromadb` as in Option A.

> **Note:** Web scrapers for Earth911 and CPCB PDFs are not included — scraping and sourcing the raw data is left to you. The `convert_to_json.py` script handles the distillation step once you have raw content.

The three collections and their purposes:

| Collection | Purpose | Fallback |
|---|---|---|
| `disposal_guides` | How to prepare and dispose each item | Exa.ai search |
| `env_facts` | Environmental impact statistics for motivational facts | Exa.ai search |
| `product_kb` | Brand/product-specific disposal notes | None |

Similarity threshold: `0.70` — results below this score trigger Exa.ai fallback instead.

---

## Session Management

Each classification response includes a `session_id` (UUID). Pass this in subsequent `/chat` calls to maintain context — EcoBot remembers the last classification and conversation history (up to 20 turns).

```
classify/text  →  returns session_id
     ↓
chat  →  pass same session_id  →  EcoBot knows what was classified
     ↓
chat  →  pass same session_id  →  conversation continues
```

Sessions are stored in memory with LRU eviction at 500 concurrent sessions. For multi-instance deployments, replace the memory store with Redis.

---

## Deployment

### Local / Docker Compose (full features)

```bash
docker compose up --build
```

Includes Ollama sidecar with persistent model storage. Recommended for local development and self-hosted deployments on Railway, Render, or HuggingFace Spaces.

### Vercel / Serverless (no Ollama)

Set `CLASSIFIER_MODE=groq` — the classifier uses LLaMA 3 70B on Groq instead of the local fine-tuned model. For ChromaDB, replace with a managed vector database (Qdrant Cloud free tier works).

```env
CLASSIFIER_MODE=groq
CHROMA_DB_PATH=...  # or swap chroma_db.py for qdrant client
```

### Platform comparison

| Platform | Ollama | ChromaDB | Recommended config |
|---|---|---|---|
| Railway | Yes | Persistent volume | `CLASSIFIER_MODE=ollama` |
| Render | Yes | Persistent disk | `CLASSIFIER_MODE=ollama` |
| HuggingFace Spaces | Yes (GPU) | Persistent storage | `CLASSIFIER_MODE=ollama` |
| Vercel | No | Qdrant Cloud | `CLASSIFIER_MODE=groq` |
| Local / Docker | Yes | Local | `CLASSIFIER_MODE=ollama` |

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with Groq (no Ollama needed)
CLASSIFIER_MODE=groq pytest tests/ -v
```

Tests require a valid `.env` file with real API keys — these are integration tests that hit the actual classification pipeline, not mocked unit tests. This was a deliberate choice: mock tests were responsible for masking real failures in previous projects.

Test coverage:
- Health endpoint schema and status
- Text classification for 6 common waste items (parametrized)
- Response schema validation (all required fields, valid enum values)
- Location-aware classification
- Session ID creation and persistence
- Input validation (empty text, text > 1000 chars)
- Batch classification (normal, too many items, empty list)
- Categories endpoint (all 7 categories present)
- Facility search (by city, with limit)
- Multi-turn chat (session continuity, empty message rejection)

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | Yes | — | Groq API key (classification + vision + response) |
| `GEMINI_API_KEY` | Yes | — | Google Gemini key (voice transcription) |
| `EXA_API_KEY` | Yes | — | Exa.ai key (RAG fallback search) |
| `CLASSIFIER_MODE` | No | `ollama` | `ollama` for local model, `groq` for serverless |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | No | `ecobot-classifier` | Model name in Ollama |
| `GROQ_RESPONSE_MODEL` | No | `llama3-70b-8192` | Model for response generation |
| `GROQ_VISION_MODEL` | No | `meta-llama/llama-4-scout-17b-16e-instruct` | Model for image identification |
| `SQLITE_DB_PATH` | No | `./data/ecobot.db` | SQLite database path |
| `CHROMA_DB_PATH` | No | `./embeddings/chroma_db` | ChromaDB persistence path |
| `RAG_SIMILARITY_THRESHOLD` | No | `0.70` | Minimum cosine similarity for RAG results |
| `RAG_TOP_K` | No | `3` | Number of RAG results to retrieve |
| `API_PORT` | No | `8000` | Server port |
| `CORS_ORIGINS` | No | `http://localhost:3000,...` | Comma-separated allowed origins |
| `MAX_BATCH_SIZE` | No | `20` | Maximum items per batch request |
| `MAX_IMAGE_SIZE_MB` | No | `10` | Maximum upload file size |
| `LOG_LEVEL` | No | `INFO` | Logging level |

---

## Frontend Integration

The backend is UI-framework agnostic. Use `docs/API.md` as the integration reference.

Recommended flows for UI builders (Lovable, Bolt, Claude Design, v0):

```
Text:  POST /classify/text → show result card with bin color

Image: POST /classify/image → show image preview + "Is this X?" confirm dialog
       POST /classify/image/confirm → show result card

Voice: POST /classify/voice → show transcription + confirm prompt
       POST /classify/voice/confirm → show result card

Chat:  POST /chat (same session_id) → append reply to conversation
```

The `natural_response` field in every classification response is a ready-to-display conversational message with bin color and disposal guidance — no additional formatting needed.

---

## Author

**Dinesh Kumar C**  
Stack: FastAPI · ChromaDB · Groq · Gemini · Ollama · SQLite · QLoRA
