"""
Validate the fine-tuning dataset for hard errors and soft warnings.
Reads data/finetuning/train.jsonl + test.jsonl and reports issues.

Run: python scraping/validate_dataset.py
     python scraping/validate_dataset.py --file data/finetuning/train.jsonl
"""
import argparse
import json
import random
import sys
from pathlib import Path

TRAIN_FILE = Path(__file__).resolve().parents[1] / "data" / "finetuning" / "train.jsonl"
TEST_FILE = Path(__file__).resolve().parents[1] / "data" / "finetuning" / "test.jsonl"

VALID_CATEGORIES = {"wet_waste", "dry_waste", "hazardous", "e_waste", "sanitary", "construction", "non_recyclable"}
VALID_BIN_COLORS = {"green", "blue", "red", "black", "grey"}

SPOT_CHECK_COUNT = 5


def load_jsonl(path: Path) -> list[dict]:
    entries = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append({"_lineno": lineno, **json.loads(line)})
            except json.JSONDecodeError as e:
                print(f"  JSON parse error at line {lineno}: {e}")
    return entries


def validate_entry(entry: dict) -> tuple[list[str], list[str]]:
    """Returns (hard_errors, soft_warnings) for a single entry."""
    errors: list[str] = []
    warnings: list[str] = []
    lineno = entry.get("_lineno", "?")
    prefix = f"line {lineno}"

    # Required top-level fields
    if not entry.get("input", "").strip():
        errors.append(f"{prefix}: empty input")
    if not entry.get("instruction", "").strip():
        errors.append(f"{prefix}: empty instruction")

    output = entry.get("output")
    if not isinstance(output, dict):
        errors.append(f"{prefix}: output is not a dict (got {type(output).__name__})")
        return errors, warnings

    # Category
    category = output.get("category", "")
    if not category:
        errors.append(f"{prefix}: missing category")
    elif category not in VALID_CATEGORIES:
        errors.append(f"{prefix}: invalid category '{category}'")

    # Bin color
    bin_color = output.get("bin_color", "")
    if not bin_color:
        errors.append(f"{prefix}: missing bin_color")
    elif bin_color not in VALID_BIN_COLORS:
        errors.append(f"{prefix}: invalid bin_color '{bin_color}'")

    # Reason
    reason = output.get("reason", "")
    if not reason:
        errors.append(f"{prefix}: missing reason")
    elif len(reason) < 15:
        warnings.append(f"{prefix}: reason too short ({len(reason)} chars): '{reason}'")

    # Preparation steps
    steps = output.get("preparation_steps", [])
    if not isinstance(steps, list) or len(steps) == 0:
        warnings.append(f"{prefix}: missing or empty preparation_steps")
    elif len(steps) < 2:
        warnings.append(f"{prefix}: only {len(steps)} preparation step(s) — consider adding more")

    # Bin label
    if not output.get("bin_label", "").strip():
        warnings.append(f"{prefix}: missing bin_label")

    return errors, warnings


def validate_file(path: Path) -> tuple[int, int, int]:
    """Returns (total, hard_error_count, soft_warning_count)."""
    print(f"\n{'='*60}")
    print(f"Validating: {path}")
    print(f"{'='*60}")

    entries = load_jsonl(path)
    if not entries:
        print("  No entries found.")
        return 0, 0, 0

    total_errors = 0
    total_warnings = 0
    error_samples: list[str] = []

    for entry in entries:
        hard, soft = validate_entry(entry)
        total_errors += len(hard)
        total_warnings += len(soft)
        for msg in hard[:2]:  # Show up to 2 errors per entry
            error_samples.append(msg)

    print(f"  Total entries:  {len(entries):,}")
    print(f"  Hard errors:    {total_errors}")
    print(f"  Soft warnings:  {total_warnings}")

    if error_samples:
        print(f"\n  First errors:")
        for msg in error_samples[:10]:
            print(f"    [ERROR] {msg}")

    # Spot-check: print N random samples
    print(f"\n  Random spot-check ({SPOT_CHECK_COUNT} samples):")
    samples = random.sample(entries, min(SPOT_CHECK_COUNT, len(entries)))
    for s in samples:
        output = s.get("output", {})
        if isinstance(output, dict):
            print(f"    input:    {s.get('input', '')[:80]}")
            print(f"    item:     {output.get('item', '?')}")
            print(f"    category: {output.get('category')}  bin: {output.get('bin_color')}")
            print(f"    reason:   {output.get('reason', '')[:80]}")
            print(f"    steps:    {len(output.get('preparation_steps', []))} step(s)")
            print()

    return len(entries), total_errors, total_warnings


def main(only_file: str | None = None) -> None:
    random.seed(42)

    files_to_check = []
    if only_file:
        p = Path(only_file)
        if not p.exists():
            print(f"File not found: {p}")
            sys.exit(1)
        files_to_check = [p]
    else:
        for p in (TRAIN_FILE, TEST_FILE):
            if p.exists():
                files_to_check.append(p)
            else:
                print(f"WARNING: {p} not found — skipping")

    if not files_to_check:
        print("No dataset files found. Run augment_dataset.py first.")
        sys.exit(1)

    grand_total = grand_errors = grand_warnings = 0
    for path in files_to_check:
        total, errors, warnings = validate_file(path)
        grand_total += total
        grand_errors += errors
        grand_warnings += warnings

    print(f"\n{'='*60}")
    print(f"SUMMARY — {len(files_to_check)} file(s)")
    print(f"  Total entries:  {grand_total:,}")
    print(f"  Hard errors:    {grand_errors}   {'✓ PASS' if grand_errors == 0 else '✗ FAIL — fix before training'}")
    print(f"  Soft warnings:  {grand_warnings}   {'✓' if grand_warnings == 0 else '(review suggested)'}")
    print(f"{'='*60}")

    if grand_errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default=None, help="Validate a single file instead of both train+test")
    args = parser.parse_args()
    main(only_file=args.file)
