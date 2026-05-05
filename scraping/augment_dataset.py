"""
Generate Alpaca-format fine-tuning dataset from disposal_guides.json + india_specific.json.
Uses LLaMA 3 8B to generate 4 phrasing variations per item, then splits 90/10 train/test.

Run: python scraping/augment_dataset.py
Output: data/finetuning/train.jsonl + data/finetuning/test.jsonl
"""
import json
import random
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from groq import Groq
from backend.config import get_settings
from backend.prompts import CLASSIFIER_SYSTEM
from scraping.tracker import mark_done, mark_failed, completed_keys

DISPOSAL_GUIDES = Path(__file__).resolve().parents[1] / "data" / "processed" / "disposal_guides.json"
INDIA_SPECIFIC = Path(__file__).resolve().parents[1] / "data" / "processed" / "india_specific.json"
TRAIN_FILE = Path(__file__).resolve().parents[1] / "data" / "finetuning" / "train.jsonl"
TEST_FILE = Path(__file__).resolve().parents[1] / "data" / "finetuning" / "test.jsonl"
PARTIAL_FILE = Path(__file__).resolve().parents[1] / "data" / "finetuning" / "augment_partial.jsonl"

VARIATIONS_PER_ITEM = 4
VARIATION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
SLEEP_BETWEEN_CALLS = 1.0
RANDOM_SEED = 42
TEST_SPLIT = 0.10
STAGE = "augment_dataset"

VARIATION_PROMPT = """Generate {n} different ways a person might ask or describe this waste item: "{item}"

Mix formal and casual language. Include:
- Casual phrasing ("my old phone", "broken charger")
- Indian English ("paani ki bottle", "kadak carton")
- Common misspellings ("baterry", "plastik bag")
- Partial descriptions ("the foil thing from medicine pack")
- Context clues ("leftover paint from renovation")

Return ONLY a JSON array of strings, no extra text."""


def build_alpaca_entry(input_text: str, output: dict) -> dict:
    return {
        "instruction": CLASSIFIER_SYSTEM,
        "input": f"Classify this waste item: {input_text}",
        "output": output,  # dict, not a JSON string
    }


def guide_to_output(guide: dict) -> dict:
    return {
        "category": guide.get("category", ""),
        "bin_color": guide.get("bin_color", ""),
        "bin_label": guide.get("bin_label", ""),
        "recyclable": guide.get("recyclable", False),
        "confidence": "high",
        "reason": guide.get("reason", ""),
        "preparation_steps": guide.get("preparation_steps", []),
        "safety_notes": guide.get("safety_notes"),
        "special_facility_required": guide.get("special_facility_required", False),
    }


def build_clients(settings) -> list[Groq]:
    keys = [settings.groq_api_key]
    if settings.groq_api_key_2:
        keys.append(settings.groq_api_key_2)
    if settings.groq_api_key_3:
        keys.append(settings.groq_api_key_3)
    return [Groq(api_key=k) for k in keys]


def generate_variations(clients: list[Groq], item: str, key_index: int) -> tuple[list[str], int]:
    n = len(clients)
    for attempt in range(n * 3):
        client = clients[key_index % n]
        key_label = f"key{(key_index % n) + 1}"
        try:
            completion = client.chat.completions.create(
                model=VARIATION_MODEL,
                messages=[
                    {"role": "user", "content": VARIATION_PROMPT.format(item=item, n=VARIATIONS_PER_ITEM)},
                ],
                temperature=0.8,
                max_tokens=512,
            )
            raw = completion.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            variations = json.loads(raw)
            return [v for v in variations if isinstance(v, str)][:VARIATIONS_PER_ITEM], (key_index + 1) % n
        except Exception as e:
            err_str = str(e)
            wait_match = re.search(r"try again in ([0-9.]+)s", err_str)
            if wait_match:
                next_key = (key_index + 1) % n
                if next_key != key_index % n:
                    print(f"  [{key_label}] rate limited -- switching to key{next_key + 1}", end=" ", flush=True)
                    key_index = next_key
                    continue
                wait = float(wait_match.group(1)) + 1
                print(f"  All keys rate limited -- waiting {wait:.0f}s...", end=" ", flush=True)
                time.sleep(wait)
                continue
            print(f"  Variation error for '{item}': {e}")
            return [], (key_index + 1) % n
    return [], (key_index + 1) % n


def load_guides() -> list[dict]:
    guides = []
    for path in (DISPOSAL_GUIDES, INDIA_SPECIFIC):
        if path.exists():
            with open(path) as f:
                data = json.load(f)
                guides.extend(data)
                print(f"  Loaded {len(data)} entries from {path.name}")
        else:
            print(f"  WARNING: {path.name} not found — skipping")
    return guides


def main() -> None:
    settings = get_settings()
    clients = build_clients(settings)
    print(f"Loaded {len(clients)} Groq API key(s) -- round-robin enabled")

    print("Loading disposal guides...")
    guides = load_guides()
    if not guides:
        print("No guides loaded -- run convert_to_json.py first.")
        sys.exit(1)

    print(f"Total guides: {len(guides)}")

    TRAIN_FILE.parent.mkdir(parents=True, exist_ok=True)

    done = completed_keys(STAGE)
    print(f"Tracker: {len(done)} items already augmented")

    # Load previously saved partial entries
    all_entries: list[dict] = []
    if PARTIAL_FILE.exists():
        with open(PARTIAL_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    all_entries.append(json.loads(line))
        print(f"Resumed {len(all_entries)} partial entries from disk")

    key_index = 0
    pending = [g for g in guides if g.get("item") and g["item"] not in done]
    print(f"Pending: {len(pending)} items")

    with open(PARTIAL_FILE, "a", encoding="utf-8") as partial_f:
        for i, guide in enumerate(pending, 1):
            item_name = guide["item"]
            print(f"[{i}/{len(pending)}] {item_name}... ", end="", flush=True)
            output = guide_to_output(guide)

            item_entries: list[dict] = [build_alpaca_entry(item_name, output)]
            for alias in guide.get("aliases", []):
                if alias:
                    item_entries.append(build_alpaca_entry(alias, output))

            variations, key_index = generate_variations(clients, item_name, key_index)
            for v in variations:
                item_entries.append(build_alpaca_entry(v, output))

            for e in item_entries:
                partial_f.write(json.dumps(e, ensure_ascii=False) + "\n")
            partial_f.flush()

            all_entries.extend(item_entries)
            mark_done(STAGE, item_name, VARIATION_MODEL, variations=len(variations))
            print(f"{len(variations)} variations  (total so far: {len(all_entries)})")
            time.sleep(SLEEP_BETWEEN_CALLS)

    # Shuffle and split
    rng = random.Random(RANDOM_SEED)
    rng.shuffle(all_entries)

    split_idx = int(len(all_entries) * (1 - TEST_SPLIT))
    train_entries = all_entries[:split_idx]
    test_entries = all_entries[split_idx:]

    def write_jsonl(path: Path, entries: list[dict]) -> None:
        with open(path, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    write_jsonl(TRAIN_FILE, train_entries)
    write_jsonl(TEST_FILE, test_entries)

    print(f"\nDone!")
    print(f"  Train: {len(train_entries):,} examples → {TRAIN_FILE}")
    print(f"  Test:  {len(test_entries):,} examples → {TEST_FILE}")


if __name__ == "__main__":
    main()
