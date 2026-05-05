# EcoBot — AI-Powered Waste Classification & Recycling Assistant

## Project Summary

EcoBot is a multimodal AI assistant for waste classification, disposal guidance, and recycling facility lookup.
It handles text, image, and voice input. Strongly focused on Indian waste practices.

**Author:** Dinesh Kumar C  
**Stack:** FastAPI · LangChain · ChromaDB · SQLite · Groq API · Gemini API · Ollama

---

## Architecture

```
User Input (text / image / voice)
         │
         ▼
   Input Processor
   ├── Text → direct
   ├── Image → LLaMA 4 Scout (Groq) → identified item text
   └── Voice → Gemini 2.0 Flash → transcribed text
         │
         ▼
   LangChain Agent  (session memory per session_id)
   ├── classify_tool   → Fine-tuned LLaMA 3 8B via Ollama  (fallback: Groq)
   ├── rag_tool        → ChromaDB disposal guides + env facts + product KB
   ├── sql_tool        → SQLite bin lookup + facility finder
   ├── vision_tool     → LLaMA 4 Scout on Groq (image path)
   ├── voice_tool      → Gemini 2.0 Flash (audio file)
   └── exa_fallback    → Exa.ai live search (low-confidence fallback)
         │
         ▼
   LLaMA 3 70B (Groq) — final response generation
         │
         ▼
   FastAPI REST + structured JSON response
```

---

## Directory Structure

```
EcoBot/
├── CLAUDE.md
├── .env.example
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── backend/
│   ├── main.py              FastAPI app entry point
│   ├── config.py            Settings / env vars (pydantic-settings)
│   ├── agent.py             LangChain agent orchestrator
│   ├── memory.py            Session memory management
│   ├── prompts.py           All system prompts
│   ├── api/
│   │   ├── classify.py      Text / image / voice / batch endpoints
│   │   ├── chat.py          Multi-turn conversation endpoint
│   │   ├── facilities.py    Facility finder endpoint
│   │   └── health.py        Health + dependency check
│   ├── tools/
│   │   ├── classify_tool.py Fine-tuned LLaMA 3 8B via Ollama
│   │   ├── rag_tool.py      ChromaDB retrieval tool
│   │   ├── sql_tool.py      SQLite bin + facility lookup
│   │   ├── vision_tool.py   LLaMA 4 Scout (Groq multimodal)
│   │   ├── voice_tool.py    Gemini 2.0 Flash transcription
│   │   └── exa_fallback.py  Exa.ai fallback search
│   ├── db/
│   │   ├── sqlite_db.py     SQLite connection + queries
│   │   └── chroma_db.py     ChromaDB client + collections
│   ├── models/
│   │   ├── requests.py      Pydantic request schemas
│   │   └── responses.py     Pydantic response schemas
│   └── middleware/
│       └── rate_limit.py    slowapi rate limiting
├── data/
│   ├── raw/
│   │   ├── earth911/        Crawl4AI scraped markdown
│   │   └── cpcb_pdfs/       Firecrawl parsed PDFs
│   ├── processed/
│   │   ├── disposal_guides.json
│   │   ├── india_specific.json
│   │   ├── env_facts.json
│   │   └── product_kb.json
│   ├── finetuning/
│   │   ├── train.jsonl      ~1800 instruction pairs
│   │   └── test.jsonl       200 held-out examples
│   ├── facilities.csv       Seed facility data (Indian cities)
│   └── waste_items.csv      Seed waste item lookup data
├── embeddings/
│   └── chroma_db/           ChromaDB persistent storage
├── scraping/
│   ├── crawl_earth911.py    Crawl4AI scraper
│   ├── crawl_cpcb.py        Firecrawl PDF parser
│   ├── convert_to_json.py   Groq distillation script
│   └── augment_dataset.py   Input variation generator
├── fine_tuning/
│   └── ecobot_finetune.ipynb  QLoRA training notebook (Colab / Kaggle)
├── scripts/
│   ├── init_db.py           Create + seed SQLite database
│   └── seed_chromadb.py     Embed processed JSON into ChromaDB
├── tests/
│   └── test_classification.py
└── docs/
    └── API.md               Full endpoint documentation
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill all values.

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` | Groq API (LLaMA 3 70B + LLaMA 4 Scout) |
| `GEMINI_API_KEY` | Google Gemini 2.0 Flash (voice transcription) |
| `EXA_API_KEY` | Exa.ai fallback search |
| `OLLAMA_BASE_URL` | Ollama endpoint (default: http://localhost:11434) |
| `OLLAMA_MODEL` | Fine-tuned model name in Ollama (default: ecobot-classifier) |
| `CLASSIFIER_MODE` | `ollama` (local) or `groq` (serverless/cloud) |
| `CHROMA_DB_PATH` | ChromaDB persistence path |
| `SQLITE_DB_PATH` | SQLite file path |
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `RATE_LIMIT` | Requests per minute per IP |

---

## Key Design Decisions

### Classifier Mode
- **`ollama`** (default): Fine-tuned LLaMA 3 8B runs locally via Ollama. Zero API cost per classification. Use for local dev and Docker deployments.
- **`groq`**: Uses `llama3-70b-8192` on Groq API. Use this for Vercel serverless or any environment where Ollama cannot run. Set `CLASSIFIER_MODE=groq`.

### Hosting Considerations

| Platform | Supported | Notes |
|---|---|---|
| **Railway** | Full (recommended) | Docker support, persistent volumes for ChromaDB + Ollama |
| **Render** | Full | Docker support, persistent disks |
| **HuggingFace Spaces** | Full | Free GPU spaces support Docker |
| **Vercel** | Partial | Set `CLASSIFIER_MODE=groq`. ChromaDB → use managed Qdrant Cloud (free tier). No Ollama. |
| **Local / Docker Compose** | Full | `docker compose up` |

### RAG Architecture
- ChromaDB with 3 collections: `disposal_guides`, `env_facts`, `product_kb`
- Embeddings: `all-MiniLM-L6-v2` (via sentence-transformers)
- Fallback threshold: similarity score < 0.7 → trigger Exa.ai
- Exact lookups (bin colors, facility data) → SQLite, NOT ChromaDB

### Session Memory
- `ConversationBufferMemory` keyed by `session_id` (UUID)
- In-memory store for single-instance deployments
- For multi-instance deployments: replace with Redis backend

### Fine-Tuned Model
- Base: `meta-llama/Meta-Llama-3-8B-Instruct`
- Method: QLoRA (rank=16, alpha=32, dropout=0.05)
- Output: LoRA adapter → merge → 4-bit GGUF → Ollama
- Classification only — NOT response generation (that's LLaMA 3 70B on Groq)

---

## Running Locally

```bash
# 1. Copy env
cp .env.example .env

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialize SQLite DB with seed data
python scripts/init_db.py

# 4. Embed knowledge base into ChromaDB
python scripts/seed_chromadb.py

# 5. (Optional) Pull and run Ollama model
ollama serve
ollama pull ecobot-classifier  # after fine-tuning

# 6. Start FastAPI
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

## Running via Docker

```bash
docker compose up --build
```

---

## Development Guidelines

- All endpoints return structured JSON matching `docs/API.md`
- Never hardcode API keys — always read from `config.py` (pydantic-settings)
- Classification always produces a `confidence` field: `high` / `medium` / `low`
- If confidence is `low`, the API includes `clarification_question` in the response
- Image and voice inputs always require a confirmation step before final classification
- Environmental facts rotate within a session (tracked in memory)
- Batch classification handles up to 20 items per request

## Waste Categories

| Category | Bin Color | Label |
|---|---|---|
| `wet_waste` | Green | Wet Waste |
| `dry_waste` | Blue | Dry Recyclable |
| `hazardous` | Red | Hazardous Waste |
| `e_waste` | Red | E-Waste |
| `sanitary` | Black | Sanitary Waste |
| `construction` | Grey | C&D Waste |
| `non_recyclable` | Grey | Non-Recyclable Reject |
