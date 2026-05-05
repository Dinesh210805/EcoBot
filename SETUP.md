# EcoBot — Setup Guide (Step by Step)

Follow these steps **in order**. Each section depends on the previous one.

---

## Step 1 — Python Environment

```bash
# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

> Requires Python 3.11+

---

## Step 2 — Configure Environment Variables

```bash
# Copy the example file
cp .env.example .env
```

Open `.env` and fill in your API keys:

| Key | Where to get it |
|---|---|
| `GROQ_API_KEY` | https://console.groq.com → API Keys |
| `GEMINI_API_KEY` | https://aistudio.google.com → Get API Key |
| `EXA_API_KEY` | https://exa.ai → Dashboard |

Leave everything else as default for local development.

> Set `CLASSIFIER_MODE=groq` for now — you don't have the fine-tuned model yet.
> Change it to `ollama` after Step 8.

---

## Step 3 — Initialize the SQLite Database

```bash
python -m scripts.init_db
```

This creates `data/ecobot.db` with three tables (`waste_items`, `facilities`, `bin_colors`)
and seeds them from `data/waste_items.csv` and `data/facilities.csv`.

Expected output:
```
Initializing EcoBot database...
[OK] Seeded N facilities
[OK] Seeded N waste items
[DB] facilities=N, waste_items=N, bin_colors=7
Done.
```

---

## Step 4 — Scrape Earth911 (Recycling Guides)

### 4a — Collect article URLs

```bash
python scraping/get_earth911_urls.py
```

Crawls earth911.com listing pages and saves all `how-to-recycle-*` article URLs.
Output: `data/raw/earth911_urls.json`
Takes ~2–5 minutes. Resumable — safe to re-run.

### 4b — Scrape each article

```bash
python scraping/crawl_earth911.py
```

Downloads and converts each article to markdown.
Output: `data/raw/earth911/` (one `.md` file per item)
Takes 30–90 minutes depending on number of articles. Resumable — skips already-scraped files.

---

## Step 5 — Scrape CPCB Government Documents

```bash
python scraping/crawl_cpcb.py
```

Fetches Indian government waste management rules:
- HTML pages via Crawl4AI
- PDF documents via pdfplumber (no API key needed)

Output: `data/raw/cpcb_pdfs/` (one `.md` file per source)
Takes ~5 minutes. Resumable.

To fetch a single source only:
```bash
python scraping/crawl_cpcb.py --source swm_rules_2016
```

---

## Step 6 — Convert Raw Markdown → Structured JSON

```bash
python scraping/convert_to_json.py
```

Uses Groq (LLaMA 4) to distill each earth911 article into a structured disposal guide JSON object.
Output: `data/processed/disposal_guides.json`

> This costs Groq API credits (~300–500 articles × 1 call each).
> Takes 15–30 minutes with 2s delay between calls. Resumable.

---

## Step 7 — Seed ChromaDB (Vector Database)

```bash
python -m scripts.seed_chromadb
```

Embeds all processed JSON into ChromaDB using `all-MiniLM-L6-v2`.

Expected output:
```
disposal_guides: N total documents
env_facts: N total documents
product_kb: N total documents
```

> `env_facts` and `product_kb` will show 0 until you add those files (see Optional Steps below).

To re-seed from scratch (clears existing data):
```bash
python -m scripts.seed_chromadb --clear
```

---

## Step 8 — Generate Fine-Tuning Dataset

```bash
python scraping/augment_dataset.py
```

Reads `disposal_guides.json` + `india_specific.json`, generates 4 phrasing variations per item via Groq (LLaMA 3 8B), and produces the training dataset.

Output:
- `data/finetuning/train.jsonl` (~1600–1800 examples)
- `data/finetuning/test.jsonl` (~180–200 examples)

Validate the dataset:
```bash
python scraping/validate_dataset.py
```

---

## Step 9 — Fine-Tune the Classifier Model

Open `fine_tuning/ecobot_finetune.ipynb` in **Kaggle** or **Google Colab** (free GPU).

Steps inside the notebook:
1. Upload `data/finetuning/train.jsonl` and `test.jsonl`
2. Run all cells — trains QLoRA on `meta-llama/Meta-Llama-3-8B-Instruct`
3. Merges LoRA adapter into the base model
4. Exports to 4-bit GGUF format
5. Download the `.gguf` file

Then register it with Ollama locally:

```bash
# Start Ollama
ollama serve

# Create a Modelfile
# (The notebook generates this — copy the output)
ollama create ecobot-classifier -f Modelfile
```

Finally update `.env`:
```
CLASSIFIER_MODE=ollama
OLLAMA_MODEL=ecobot-classifier
```

---

## Step 10 — Start the Server

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

API is live at `http://localhost:8000`

| URL | Purpose |
|---|---|
| `http://localhost:8000/docs` | Swagger UI — test all endpoints interactively |
| `http://localhost:8000/api/v1/health` | Health check — confirms all dependencies |
| `http://localhost:8000/api/v1/categories` | List all waste categories |

---

## Step 11 — Verify Everything Works

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Test classification
curl -X POST http://localhost:8000/api/v1/classify/text \
  -H "Content-Type: application/json" \
  -d '{"text": "old newspaper", "include_facilities": false}'

# Test RAG retrieval
python scraping/test_retrieval.py
```

---

## Optional Steps

### Add Environmental Facts

Create `data/processed/env_facts.json` as a JSON array:

```json
[
  {
    "id": "fact_001",
    "text": "Recycling one tonne of paper saves 17 trees and 26,000 litres of water.",
    "metadata": {"category": "paper", "source": "CPCB"}
  }
]
```

Then re-run `python -m scripts.seed_chromadb` to ingest.

### Add Product Knowledge Base

Create `data/processed/product_kb.json` with brand-specific recycling info:

```json
[
  {
    "id": "prod_001",
    "text": "Tetra Pak cartons are accepted at select drop-off points in major Indian cities. Remove straws before recycling.",
    "metadata": {"brand": "Tetra Pak", "category": "dry_waste"}
  }
]
```

Then re-run `python -m scripts.seed_chromadb`.

### Run via Docker

```bash
docker compose up --build
```

---

## Quick Reference — Run Order

```
Step 1   pip install -r requirements.txt
Step 2   fill in .env
Step 3   python -m scripts.init_db
Step 4a  python scraping/get_earth911_urls.py
Step 4b  python scraping/crawl_earth911.py
Step 5   python scraping/crawl_cpcb.py
Step 6   python scraping/convert_to_json.py
Step 7   python -m scripts.seed_chromadb
Step 8   python scraping/augment_dataset.py
Step 9   fine_tuning/ecobot_finetune.ipynb  (Kaggle/Colab)
Step 10  uvicorn backend.main:app --reload
Step 11  curl http://localhost:8000/api/v1/health
```

Steps 4–8 only need to be run **once** to build the knowledge base and training data.
After that, only Step 10 is needed to run the server.
