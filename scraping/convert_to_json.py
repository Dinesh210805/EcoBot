"""
Convert raw scraped markdown files into structured JSON for ChromaDB seeding.
Uses Groq LLaMA 3 70B to distill content into {id, text, metadata} format.

Run: python scraping/convert_to_json.py --input data/raw/earth911 --output data/processed/disposal_guides.json
"""
import argparse
import json
import uuid
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from groq import Groq
from backend.config import get_settings

settings = get_settings()
client = Groq(api_key=settings.groq_api_key)

DISTILL_PROMPT = """You are a data extraction assistant. Given raw markdown about waste disposal,
extract clean, concise disposal guide entries.

Return a JSON array of objects:
[
  {
    "id": "<unique slug>",
    "text": "<2-4 sentence disposal guide focusing on how to dispose correctly>",
    "metadata": {
      "item": "<waste item name>",
      "category": "<wet_waste|dry_waste|hazardous|e_waste|sanitary|construction|non_recyclable>",
      "source": "<filename>"
    }
  }
]

Rules:
- Each entry covers ONE specific waste item
- text must be actionable disposal instructions
- Return ONLY valid JSON, no extra text"""


def distill_file(md_path: Path) -> list[dict]:
    content = md_path.read_text(encoding="utf-8")[:4000]  # limit tokens
    completion = client.chat.completions.create(
        model=settings.groq_classifier_model,
        messages=[
            {"role": "system", "content": DISTILL_PROMPT},
            {"role": "user", "content": f"Source: {md_path.name}\n\n{content}"},
        ],
        temperature=0.2,
        max_tokens=2048,
    )
    raw = completion.choices[0].message.content.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    entries = json.loads(raw)
    # Ensure unique IDs
    for e in entries:
        if not e.get("id"):
            e["id"] = str(uuid.uuid4())
    return entries


def process_directory(input_dir: Path, output_file: Path):
    md_files = list(input_dir.glob("*.md")) + list(input_dir.glob("*.txt"))
    if not md_files:
        print(f"No markdown files found in {input_dir}")
        return

    all_entries = []
    for i, path in enumerate(md_files, 1):
        print(f"[{i}/{len(md_files)}] Processing {path.name}...")
        try:
            entries = distill_file(path)
            all_entries.extend(entries)
            print(f"  → {len(entries)} entries extracted")
        except Exception as e:
            print(f"  ERROR: {e}")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_entries, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(all_entries)} entries to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Directory with raw markdown files")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    args = parser.parse_args()

    process_directory(Path(args.input), Path(args.output))
