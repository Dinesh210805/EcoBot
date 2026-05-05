import sqlite3
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Optional
from backend.config import get_settings

settings = get_settings()


@contextmanager
def get_db():
    db_path = Path(settings.sqlite_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_schema():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS waste_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                aliases TEXT DEFAULT '[]',
                category TEXT NOT NULL,
                sub_category TEXT,
                bin_color TEXT NOT NULL,
                bin_label TEXT NOT NULL,
                hazardous INTEGER DEFAULT 0,
                recyclable INTEGER DEFAULT 0,
                preparation_steps TEXT DEFAULT '[]',
                safety_notes TEXT,
                special_facility_required INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS facilities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                address TEXT NOT NULL,
                city TEXT NOT NULL,
                pincode TEXT,
                latitude REAL,
                longitude REAL,
                accepted_categories TEXT DEFAULT '[]',
                operating_hours TEXT,
                contact TEXT,
                verified INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS bin_colors (
                category TEXT PRIMARY KEY,
                bin_color TEXT NOT NULL,
                bin_label TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_facilities_city ON facilities(city);
            CREATE INDEX IF NOT EXISTS idx_waste_items_category ON waste_items(category);
        """)
        _seed_bin_colors(conn)


def _seed_bin_colors(conn: sqlite3.Connection):
    colors = [
        ("wet_waste", "green", "Wet Waste"),
        ("dry_waste", "blue", "Dry Recyclable"),
        ("hazardous", "red", "Hazardous Waste"),
        ("e_waste", "red", "E-Waste"),
        ("sanitary", "black", "Sanitary Waste"),
        ("construction", "grey", "C&D Waste"),
        ("non_recyclable", "grey", "Non-Recyclable Reject"),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO bin_colors(category, bin_color, bin_label) VALUES (?,?,?)",
        colors
    )


def get_bin_info(category: str) -> dict:
    with get_db() as conn:
        row = conn.execute(
            "SELECT bin_color, bin_label FROM bin_colors WHERE category = ?", (category,)
        ).fetchone()
        if row:
            return {"bin_color": row["bin_color"], "bin_label": row["bin_label"]}
        return {"bin_color": "grey", "bin_label": "General Waste"}


def search_facilities(
    city: Optional[str] = None,
    pincode: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 5,
) -> list[dict]:
    clauses = []
    params: list = []

    if city:
        clauses.append("LOWER(city) = LOWER(?)")
        params.append(city)
    if pincode:
        clauses.append("pincode = ?")
        params.append(pincode)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM facilities {where} ORDER BY verified DESC LIMIT ?", params
        ).fetchall()

    results = []
    for row in rows:
        facility = dict(row)
        facility["accepted_categories"] = json.loads(facility["accepted_categories"] or "[]")
        if category and category not in facility["accepted_categories"]:
            continue
        facility["verified"] = bool(facility["verified"])
        results.append(facility)

    return results[:limit]


def insert_facility(data: dict):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO facilities
               (name, address, city, pincode, latitude, longitude,
                accepted_categories, operating_hours, contact, verified)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                data["name"], data["address"], data["city"], data.get("pincode"),
                data.get("latitude"), data.get("longitude"),
                json.dumps(data.get("accepted_categories", [])),
                data.get("operating_hours"), data.get("contact"),
                int(data.get("verified", False)),
            ),
        )


def insert_waste_item(data: dict):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO waste_items
               (name, aliases, category, sub_category, bin_color, bin_label,
                hazardous, recyclable, preparation_steps, safety_notes, special_facility_required)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                data["name"], json.dumps(data.get("aliases", [])),
                data["category"], data.get("sub_category"),
                data["bin_color"], data["bin_label"],
                int(data.get("hazardous", False)), int(data.get("recyclable", False)),
                json.dumps(data.get("preparation_steps", [])),
                data.get("safety_notes"),
                int(data.get("special_facility_required", False)),
            ),
        )
