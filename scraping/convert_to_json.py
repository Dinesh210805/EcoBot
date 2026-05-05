"""
Convert raw scraped earth911 markdown files into structured disposal guide JSON.
Uses Groq LLaMA 3 8B (round-robin across up to 3 API keys) to distill each
article into a typed disposal guide entry.

Run: python scraping/convert_to_json.py
     python scraping/convert_to_json.py --limit 10  # test with a small batch
Output: data/processed/disposal_guides.json
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from groq import Groq
from backend.config import get_settings
from scraping.tracker import mark_done, mark_failed, completed_keys

INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "earth911"
OUTPUT_FILE = Path(__file__).resolve().parents[1] / "data" / "processed" / "disposal_guides.json"

SLEEP_BETWEEN_CALLS = 1.0
MAX_RETRIES_PER_KEY = 4
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
STAGE = "convert_to_json"

DISTILL_PROMPT = """You are a waste disposal data extraction expert. Given raw markdown scraped from an earth911.com recycling guide page, extract a structured disposal guide entry.

Return a JSON object with EXACTLY this schema:
{
  "item": "<primary name of the waste item>",
  "aliases": ["<alternative name 1>", "<alternative name 2>"],
  "category": "<one of: wet_waste | dry_waste | hazardous | e_waste | sanitary | construction | non_recyclable>",
  "bin_color": "<one of: green | blue | red | black | grey>",
  "bin_label": "<human-readable bin label, e.g. 'Wet Waste', 'Dry Recyclable', 'Hazardous Waste'>",
  "recyclable": true or false,
  "reason": "<1-2 sentence explanation of why it goes in that bin>",
  "preparation_steps": ["<step 1>", "<step 2>", "<step 3>"],
  "safety_notes": "<safety warning if hazardous, or null>",
  "special_facility_required": true or false
}

Category mapping:
- wet_waste -> green bin (food scraps, garden waste, organic)
- dry_waste -> blue bin (paper, cardboard, glass, clean plastic, metal)
- hazardous -> red bin (batteries, chemicals, paint, pesticides, motor oil)
- e_waste -> red bin (electronics, cables, appliances)
- sanitary -> black bin (diapers, sanitary pads, medical waste)
- construction -> grey bin (rubble, tiles, wood from demolition)
- non_recyclable -> grey bin (contaminated/multi-layer plastics, dirty packaging)

Rules:
- preparation_steps must have at least 1 step
- reason must be at least 15 characters
- Return ONLY valid JSON, no markdown fences, no extra text"""


def build_clients(settings) -> list[Groq]:
    """Build Groq clients for all configured API keys."""
    keys = [settings.groq_api_key]
    if settings.groq_api_key_2:
        keys.append(settings.groq_api_key_2)
    if settings.groq_api_key_3:
        keys.append(settings.groq_api_key_3)
    return [Groq(api_key=k) for k in keys]


def distill_file(clients: list[Groq], md_path: Path, key_index: int) -> tuple[dict | None, int]:
    """
    Distill a markdown file into a structured entry.
    Returns (entry_or_None, next_key_index).
    Rotates to next key on rate-limit; skips exhausted keys.
    """
    content = md_path.read_text(encoding="utf-8")[:3000]
    n = len(clients)

    for attempt in range(n * MAX_RETRIES_PER_KEY):
        client = clients[key_index % n]
        key_label = f"key{(key_index % n) + 1}"
        try:
            completion = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": DISTILL_PROMPT},
                    {"role": "user", "content": f"Source file: {md_path.name}\n\n{content}"},
                ],
                temperature=0.1,
                max_tokens=1024,
            )
            raw = completion.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()

            if not raw:
                # Empty response — rotate key and retry
                print(f"  [{key_label}] empty response, retrying with next key...", end=" ", flush=True)
                key_index = (key_index + 1) % n
                time.sleep(1)
                continue

            # Extract the first complete JSON object (handles trailing text)
            brace_match = re.search(r"\{[\s\S]*\}", raw)
            if brace_match:
                raw = brace_match.group(0)

            entry = json.loads(raw)
            entry["source_file"] = md_path.name
            return entry, (key_index + 1) % n
        except json.JSONDecodeError as e:
            # Malformed JSON — retry with next key once, then give up
            print(f"  JSON parse error ({e}) — retrying...", end=" ", flush=True)
            key_index = (key_index + 1) % n
            time.sleep(1)
            continue
        except Exception as e:
            err_str = str(e)
            wait_match = re.search(r"try again in ([0-9.]+)s", err_str)
            if wait_match:
                wait = float(wait_match.group(1)) + 1
                # Try switching to next key immediately instead of waiting
                next_key = (key_index + 1) % n
                if next_key != key_index % n:
                    print(f"  [{key_label}] rate limited — switching to key{next_key + 1}")
                    key_index = next_key
                    continue
                # All keys tried for this window — wait it out
                print(f"  All keys rate limited — waiting {wait:.0f}s...")
                time.sleep(wait)
                continue
            print(f"  [{key_label}] API error: {e}")
            return None, (key_index + 1) % n

    print("  Max retries exceeded across all keys")
    return None, (key_index + 1) % n


def main(limit: int | None = None) -> None:
    settings = get_settings()
    clients = build_clients(settings)
    print(f"Loaded {len(clients)} Groq API key(s) — round-robin enabled")

    if not INPUT_DIR.exists():
        print(f"Input directory not found: {INPUT_DIR}")
        print("Run scraping/crawl_earth911.py first.")
        sys.exit(1)

    md_files = sorted(INPUT_DIR.glob("*.md"))
    if not md_files:
        print(f"No markdown files in {INPUT_DIR}")
        sys.exit(1)

    done = completed_keys(STAGE)
    print(f"Tracker: {len(done)} already completed")

    existing: dict[str, dict] = {}
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            for entry in json.load(f):
                if entry.get("source_file"):
                    existing[entry["source_file"]] = entry

    pending = [f for f in md_files if f.name not in done]
    if limit:
        pending = pending[:limit]

    print(f"Files total: {len(md_files)}  |  pending: {len(pending)}")

    all_entries = list(existing.values())
    errors = 0
    key_index = 0

    for i, path in enumerate(pending, 1):
        print(f"[{i}/{len(pending)}] {path.name}... ", end="", flush=True)
        entry, key_index = distill_file(clients, path, key_index)
        if entry:
            all_entries.append(entry)
            mark_done(STAGE, path.name, MODEL, item=entry.get("item", ""))
            print(f"OK -- {entry.get('item', '?')} ({entry.get('category', '?')})")
        else:
            mark_failed(STAGE, path.name, MODEL)
            errors += 1
            print("FAILED")

        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_entries, f, indent=2, ensure_ascii=False)

        if i < len(pending):
            time.sleep(SLEEP_BETWEEN_CALLS)

    print(f"\nDone -- {len(all_entries)} entries saved  |  {errors} errors")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Process only N files (for testing)")
    args = parser.parse_args()
    main(limit=args.limit)
