"""
Initialize SQLite database and seed waste_items + facilities from CSV files.
Run: python -m scripts.init_db
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.db.sqlite_db import init_schema, insert_facility, insert_waste_item, get_db

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def seed_facilities():
    csv_path = DATA_DIR / "facilities.csv"
    if not csv_path.exists():
        print(f"[SKIP] {csv_path} not found")
        return

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            row["accepted_categories"] = json.loads(row.get("accepted_categories", "[]"))
            row["latitude"] = float(row["latitude"]) if row.get("latitude") else None
            row["longitude"] = float(row["longitude"]) if row.get("longitude") else None
            row["verified"] = row.get("verified", "0") in ("1", "true", "True")
            insert_facility(row)
            count += 1
    print(f"[OK] Seeded {count} facilities")


def seed_waste_items():
    csv_path = DATA_DIR / "waste_items.csv"
    if not csv_path.exists():
        print(f"[SKIP] {csv_path} not found")
        return

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            row["aliases"] = json.loads(row.get("aliases", "[]"))
            row["preparation_steps"] = json.loads(row.get("preparation_steps", "[]"))
            row["hazardous"] = row.get("hazardous", "0") in ("1", "true", "True")
            row["recyclable"] = row.get("recyclable", "0") in ("1", "true", "True")
            row["special_facility_required"] = row.get("special_facility_required", "0") in ("1", "true", "True")
            insert_waste_item(row)
            count += 1
    print(f"[OK] Seeded {count} waste items")


def verify():
    with get_db() as conn:
        facilities = conn.execute("SELECT COUNT(*) FROM facilities").fetchone()[0]
        items = conn.execute("SELECT COUNT(*) FROM waste_items").fetchone()[0]
        bins = conn.execute("SELECT COUNT(*) FROM bin_colors").fetchone()[0]
    print(f"[DB] facilities={facilities}, waste_items={items}, bin_colors={bins}")


if __name__ == "__main__":
    print("Initializing EcoBot database...")
    init_schema()
    seed_facilities()
    seed_waste_items()
    verify()
    print("Done.")
