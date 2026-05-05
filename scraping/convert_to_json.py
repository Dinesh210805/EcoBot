"""
Convert raw scraped earth911 markdown files into structured disposal guide JSON.
Uses Groq LLaMA 3 70B to distill each article into a typed disposal guide entry.

Run: python scraping/convert_to_json.py
     python scraping/convert_to_json.py --limit 10  # test with a small batch
Output: data/processed/disposal_guides.json
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from groq import Groq
from backend.config import get_settings

INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "earth911"
OUTPUT_FILE = Path(__file__).resolve().parents[1] / "data" / "processed" / "disposal_guides.json"

SLEEP_BETWEEN_CALLS = 2.0  # stay under Groq RPM for 70B

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
- wet_waste → green bin (food scraps, garden waste, organic)
- dry_waste → blue bin (paper, cardboard, glass, clean plastic, metal)
- hazardous → red bin (batteries, chemicals, paint, pesticides, motor oil)
- e_waste → red bin (electronics, cables, appliances)
- sanitary → black bin (diapers, sanitary pads, medical waste)
- construction → grey bin (rubble, tiles, wood from demolition)
- non_recyclable → grey bin (contaminated/multi-layer plastics, dirty packaging)

Rules:
- preparation_steps must have at least 1 step
- reason must be at least 15 characters
- Return ONLY valid JSON, no markdown fences, no extra text"""


def distill_file(client: Groq, model: str, md_path: Path) -> dict | None:
    content = md_path.read_text(encoding="utf-8")[:3000]

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": DISTILL_PROMPT},
                {"role": "user", "content": f"Source file: {md_path.name}\n\n{content}"},
            ],
            temperature=0.1,
            max_tokens=1024,
        )
        raw = completion.choices[0].message.content.strip()
        # Strip markdown fences if the model ignores our instruction
        raw = raw.replace("```json", "").replace("```", "").strip()
        entry = json.loads(raw)
        entry["source_file"] = md_path.name
        return entry
    except json.JSONDecodeError as e:
        print(f"  JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"  API error: {e}")
        return None


def main(limit: int | None = None) -> None:
    settings = get_settings()
    client = Groq(api_key=settings.groq_api_key)
    model = "llama3-70b-8192"

    if not INPUT_DIR.exists():
        print(f"Input directory not found: {INPUT_DIR}")
        print("Run scraping/crawl_earth911.py first.")
        sys.exit(1)

    md_files = sorted(INPUT_DIR.glob("*.md"))
    if not md_files:
        print(f"No markdown files in {INPUT_DIR}")
        sys.exit(1)

    # Load existing output to allow resumable runs
    existing: dict[str, dict] = {}
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            for entry in json.load(f):
                if entry.get("source_file"):
                    existing[entry["source_file"]] = entry
        print(f"Resuming — {len(existing)} entries already processed")

    pending = [f for f in md_files if f.name not in existing]
    if limit:
        pending = pending[:limit]

    print(f"Files total: {len(md_files)}  |  pending: {len(pending)}")

    all_entries = list(existing.values())
    errors = 0

    for i, path in enumerate(pending, 1):
        print(f"[{i}/{len(pending)}] {path.name}… ", end="", flush=True)
        entry = distill_file(client, model, path)
        if entry:
            all_entries.append(entry)
            print(f"OK — {entry.get('item', '?')} ({entry.get('category', '?')})")
        else:
            errors += 1
            print("FAILED")

        # Persist after every file
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_entries, f, indent=2, ensure_ascii=False)

        if i < len(pending):
            time.sleep(SLEEP_BETWEEN_CALLS)

    print(f"\nDone — {len(all_entries)} entries saved  |  {errors} errors")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Process only N files (for testing)")
    args = parser.parse_args()
    main(limit=args.limit)
