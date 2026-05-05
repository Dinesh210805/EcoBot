"""
Centralized pipeline tracker — shared by all data pipeline scripts.
Reads/writes data/pipeline_tracker.json.
"""
import json
from datetime import datetime
from pathlib import Path

TRACKER_FILE = Path(__file__).resolve().parents[1] / "data" / "pipeline_tracker.json"


def load() -> dict:
    if TRACKER_FILE.exists():
        with open(TRACKER_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save(tracker: dict) -> None:
    TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRACKER_FILE, "w", encoding="utf-8") as f:
        json.dump(tracker, f, indent=2, ensure_ascii=False)


def mark_done(stage: str, key: str, model: str, **extra) -> None:
    tracker = load()
    tracker.setdefault(stage, {})[key] = {
        "status": "completed",
        "model": model,
        "completed_at": datetime.now().isoformat(timespec="seconds"),
        **extra,
    }
    _save(tracker)


def mark_failed(stage: str, key: str, model: str) -> None:
    tracker = load()
    existing = tracker.setdefault(stage, {}).get(key, {})
    if existing.get("status") != "completed":
        tracker[stage][key] = {
            "status": "failed",
            "model": model,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        _save(tracker)


def completed_keys(stage: str) -> set[str]:
    tracker = load()
    return {k for k, v in tracker.get(stage, {}).items() if v.get("status") == "completed"}


def failed_keys(stage: str) -> set[str]:
    tracker = load()
    return {k for k, v in tracker.get(stage, {}).items() if v.get("status") == "failed"}
