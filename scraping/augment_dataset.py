"""
Generate training data augmentation — creates input variations for fine-tuning.
Takes the waste_items.csv and generates Alpaca-format instruction pairs.

Run: python scraping/augment_dataset.py --output data/finetuning/train_augmented.jsonl --per-item 5
"""
import argparse
import csv
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from groq import Groq
from backend.config import get_settings
from backend.prompts import CLASSIFIER_SYSTEM

settings = get_settings()
client = Groq(api_key=settings.groq_api_key)

VARIATION_PROMPT = """Generate {n} different ways a person might describe or ask about this waste item: "{item}"

Include casual language, Indian English, common misspellings, partial descriptions.
Examples: "old phone", "my samsung died", "broken charger wire", "paani ki bottle"

Return a JSON array of strings. Return ONLY the array."""

WASTE_ITEMS_CSV = Path(__file__).resolve().parents[1] / "data" / "waste_items.csv"


def generate_variations(item: str, n: int) -> list[str]:
    completion = client.chat.completions.create(
        model=settings.groq_classifier_model,
        messages=[
            {"role": "user", "content": VARIATION_PROMPT.format(item=item, n=n)},
        ],
        temperature=0.9,
        max_tokens=512,
    )
    raw = completion.choices[0].message.content.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    variations = json.loads(raw)
    return [v for v in variations if isinstance(v, str)]


def build_alpaca_entry(input_text: str, output: dict) -> dict:
    return {
        "instruction": CLASSIFIER_SYSTEM,
        "input": f"Classify this waste item: {input_text}",
        "output": json.dumps(output, ensure_ascii=False),
    }


def load_waste_items() -> list[dict]:
    items = []
    with open(WASTE_ITEMS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            items.append(row)
    return items


def main(output_file: Path, per_item: int):
    items = load_waste_items()
    output_file.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    with open(output_file, "w", encoding="utf-8") as out:
        for i, item in enumerate(items, 1):
            print(f"[{i}/{len(items)}] {item['name']}...")

            # Build the ground-truth output
            gt_output = {
                "category": item["category"],
                "bin_color": item["bin_color"],
                "bin_label": item["bin_label"],
                "recyclable": item["recyclable"] in ("1", "true", "True", True),
                "confidence": "high",
                "reason": f"{item['name']} is {item['category'].replace('_', ' ')}.",
                "preparation_steps": json.loads(item.get("preparation_steps", "[]")),
                "safety_notes": item.get("safety_notes") or None,
                "special_facility_required": item["special_facility_required"] in ("1", "true", "True", True),
            }

            # Canonical name entry
            entry = build_alpaca_entry(item["name"], gt_output)
            out.write(json.dumps(entry, ensure_ascii=False) + "\n")
            total += 1

            # Alias entries
            aliases = json.loads(item.get("aliases", "[]"))
            for alias in aliases:
                entry = build_alpaca_entry(alias, gt_output)
                out.write(json.dumps(entry, ensure_ascii=False) + "\n")
                total += 1

            # LLM-generated variations
            try:
                variations = generate_variations(item["name"], per_item)
                for v in variations:
                    entry = build_alpaca_entry(v, gt_output)
                    out.write(json.dumps(entry, ensure_ascii=False) + "\n")
                    total += 1
            except Exception as e:
                print(f"  Variation generation failed: {e}")

    print(f"\nGenerated {total} training examples → {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/finetuning/train_augmented.jsonl")
    parser.add_argument("--per-item", type=int, default=5)
    args = parser.parse_args()
    main(Path(args.output), args.per_item)
