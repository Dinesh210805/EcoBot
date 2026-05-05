"""
Show a terminal summary of the EcoBot data pipeline tracker.
Reads data/pipeline_tracker.json and prints per-stage progress.

Run: python scripts/pipeline_status.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scraping.tracker import load, TRACKER_FILE

# Known stages in pipeline order
STAGE_META = {
    "convert_to_json": {
        "label": "1. Distill → disposal_guides.json",
        "total_source": Path(__file__).resolve().parents[1] / "data" / "raw" / "earth911",
        "unit": "md files",
    },
    "augment_dataset": {
        "label": "2. Augment → finetuning JSONL",
        "total_source": None,
        "unit": "guide items",
    },
}

WIDTH = 60


def bar(done: int, total: int, width: int = 30) -> str:
    if total == 0:
        return "[" + "-" * width + "] n/a"
    filled = int(width * done / total)
    return f"[{'█' * filled}{'░' * (width - filled)}] {done}/{total}"


def fmt_time(iso: str) -> str:
    return iso.replace("T", " ")


def main() -> None:
    tracker = load()

    if not tracker:
        print(f"No tracker data found at {TRACKER_FILE}")
        print("Run scraping scripts first.")
        return

    print("=" * WIDTH)
    print("  EcoBot Pipeline Status")
    print(f"  Tracker: {TRACKER_FILE}")
    print("=" * WIDTH)

    for stage, meta in STAGE_META.items():
        items = tracker.get(stage, {})
        completed = [k for k, v in items.items() if v.get("status") == "completed"]
        failed = [k for k, v in items.items() if v.get("status") == "failed"]

        # Determine total from source directory if available
        total = 0
        if meta["total_source"] and Path(meta["total_source"]).exists():
            if stage == "convert_to_json":
                total = len(list(Path(meta["total_source"]).glob("*.md")))
            else:
                total = len(completed) + len(failed)  # best estimate
        else:
            total = len(completed) + len(failed)

        print(f"\n{meta['label']}")
        print(f"  {bar(len(completed), total)}")
        if failed:
            print(f"  Failed:    {len(failed)}")
        if completed:
            # Most recent completion
            last = max(
                (v for v in items.values() if v.get("status") == "completed"),
                key=lambda v: v.get("completed_at", ""),
            )
            model = last.get("model", "?")
            ts = fmt_time(last.get("completed_at", "?"))
            print(f"  Model:     {model}")
            print(f"  Last done: {ts}")

        pending_count = max(0, total - len(completed) - len(failed))
        if pending_count:
            print(f"  Remaining: {pending_count} {meta['unit']}")

    # Any stages in tracker not in our known list
    extra = set(tracker.keys()) - set(STAGE_META.keys())
    for stage in sorted(extra):
        items = tracker[stage]
        completed = sum(1 for v in items.values() if v.get("status") == "completed")
        failed = sum(1 for v in items.values() if v.get("status") == "failed")
        print(f"\n{stage} (unlisted stage)")
        print(f"  Completed: {completed}  Failed: {failed}")

    print("\n" + "=" * WIDTH)

    # Failed items detail
    for stage in STAGE_META:
        items = tracker.get(stage, {})
        failed_items = [k for k, v in items.items() if v.get("status") == "failed"]
        if failed_items:
            print(f"\nFailed in {stage}:")
            for name in failed_items[:20]:
                print(f"  - {name}")
            if len(failed_items) > 20:
                print(f"  ... and {len(failed_items) - 20} more")


if __name__ == "__main__":
    main()
