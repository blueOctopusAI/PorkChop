"""SQLite database for bill storage and analysis results."""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional


DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "data" / "porkchop.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS bills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    congress INTEGER NOT NULL,
    bill_type TEXT NOT NULL,
    bill_number INTEGER NOT NULL,
    title TEXT,
    short_title TEXT,
    status TEXT,
    introduced_date TEXT,
    sponsors TEXT,
    cosponsors_count INTEGER DEFAULT 0,
    subjects TEXT,
    summary TEXT,
    source TEXT,
    fetched_at TEXT DEFAULT (datetime('now')),
    UNIQUE(congress, bill_type, bill_number)
);

CREATE TABLE IF NOT EXISTS bill_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id INTEGER NOT NULL REFERENCES bills(id),
    version_code TEXT NOT NULL,
    version_name TEXT,
    raw_text TEXT,
    cleaned_text TEXT,
    xml_text TEXT,
    text_url TEXT,
    xml_url TEXT,
    fetched_at TEXT DEFAULT (datetime('now')),
    UNIQUE(bill_id, version_code)
);

CREATE TABLE IF NOT EXISTS sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id INTEGER NOT NULL REFERENCES bills(id),
    version_id INTEGER REFERENCES bill_versions(id),
    section_number TEXT,
    title TEXT,
    text TEXT NOT NULL,
    parent_id INTEGER REFERENCES sections(id),
    level TEXT,
    position INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS spending_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id INTEGER REFERENCES sections(id),
    bill_id INTEGER NOT NULL REFERENCES bills(id),
    amount TEXT NOT NULL,
    amount_numeric REAL,
    purpose TEXT,
    recipient TEXT,
    availability TEXT,
    fiscal_years TEXT,
    source_text TEXT
);

CREATE TABLE IF NOT EXISTS legal_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id INTEGER REFERENCES sections(id),
    bill_id INTEGER NOT NULL REFERENCES bills(id),
    ref_type TEXT NOT NULL,
    ref_text TEXT NOT NULL,
    title_code TEXT,
    section_code TEXT
);

CREATE TABLE IF NOT EXISTS deadlines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id INTEGER REFERENCES sections(id),
    bill_id INTEGER NOT NULL REFERENCES bills(id),
    date TEXT,
    action TEXT,
    responsible_entity TEXT,
    source_text TEXT
);

CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id INTEGER REFERENCES sections(id),
    bill_id INTEGER NOT NULL REFERENCES bills(id),
    name TEXT NOT NULL,
    entity_type TEXT,
    role TEXT
);

CREATE TABLE IF NOT EXISTS summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id INTEGER NOT NULL REFERENCES bills(id),
    section_id INTEGER REFERENCES sections(id),
    summary_text TEXT NOT NULL,
    model_used TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pork_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spending_item_id INTEGER REFERENCES spending_items(id),
    bill_id INTEGER NOT NULL REFERENCES bills(id),
    score INTEGER NOT NULL,
    reasons TEXT,
    flags TEXT,
    model_used TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS comparisons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id INTEGER NOT NULL REFERENCES bills(id),
    from_version_id INTEGER NOT NULL REFERENCES bill_versions(id),
    to_version_id INTEGER NOT NULL REFERENCES bill_versions(id),
    additions_count INTEGER DEFAULT 0,
    removals_count INTEGER DEFAULT 0,
    changes_json TEXT,
    spending_diff_json TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_sections_bill ON sections(bill_id);
CREATE INDEX IF NOT EXISTS idx_spending_bill ON spending_items(bill_id);
CREATE INDEX IF NOT EXISTS idx_refs_bill ON legal_references(bill_id);
CREATE INDEX IF NOT EXISTS idx_deadlines_bill ON deadlines(bill_id);
CREATE INDEX IF NOT EXISTS idx_entities_bill ON entities(bill_id);
CREATE INDEX IF NOT EXISTS idx_summaries_bill ON summaries(bill_id);
CREATE INDEX IF NOT EXISTS idx_pork_bill ON pork_scores(bill_id);
"""


class Database:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # --- Bills ---

    def upsert_bill(self, congress: int, bill_type: str, bill_number: int, **kwargs) -> int:
        with self.connect() as conn:
            existing = conn.execute(
                "SELECT id FROM bills WHERE congress=? AND bill_type=? AND bill_number=?",
                (congress, bill_type, bill_number),
            ).fetchone()
            if existing:
                if kwargs:
                    sets = ", ".join(f"{k}=?" for k in kwargs)
                    conn.execute(
                        f"UPDATE bills SET {sets} WHERE id=?",
                        (*kwargs.values(), existing["id"]),
                    )
                return existing["id"]
            cols = ["congress", "bill_type", "bill_number"] + list(kwargs.keys())
            placeholders = ", ".join("?" for _ in cols)
            col_str = ", ".join(cols)
            cur = conn.execute(
                f"INSERT INTO bills ({col_str}) VALUES ({placeholders})",
                (congress, bill_type, bill_number, *kwargs.values()),
            )
            return cur.lastrowid

    def get_bill(self, bill_id: int) -> Optional[dict]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM bills WHERE id=?", (bill_id,)).fetchone()
            return dict(row) if row else None

    def find_bill(self, congress: int, bill_type: str, bill_number: int) -> Optional[dict]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM bills WHERE congress=? AND bill_type=? AND bill_number=?",
                (congress, bill_type, bill_number),
            ).fetchone()
            return dict(row) if row else None

    def list_bills(self, limit: int = 50) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM bills ORDER BY fetched_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def search_bills(self, query: str) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM bills WHERE title LIKE ? OR short_title LIKE ? OR summary LIKE ?",
                (f"%{query}%", f"%{query}%", f"%{query}%"),
            ).fetchall()
            return [dict(r) for r in rows]

    # --- Versions ---

    def upsert_version(self, bill_id: int, version_code: str, **kwargs) -> int:
        with self.connect() as conn:
            existing = conn.execute(
                "SELECT id FROM bill_versions WHERE bill_id=? AND version_code=?",
                (bill_id, version_code),
            ).fetchone()
            if existing:
                if kwargs:
                    sets = ", ".join(f"{k}=?" for k in kwargs)
                    conn.execute(
                        f"UPDATE bill_versions SET {sets} WHERE id=?",
                        (*kwargs.values(), existing["id"]),
                    )
                return existing["id"]
            cols = ["bill_id", "version_code"] + list(kwargs.keys())
            placeholders = ", ".join("?" for _ in cols)
            col_str = ", ".join(cols)
            cur = conn.execute(
                f"INSERT INTO bill_versions ({col_str}) VALUES ({placeholders})",
                (bill_id, version_code, *kwargs.values()),
            )
            return cur.lastrowid

    def get_versions(self, bill_id: int) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM bill_versions WHERE bill_id=? ORDER BY fetched_at",
                (bill_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_version(self, version_id: int) -> Optional[dict]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM bill_versions WHERE id=?", (version_id,)
            ).fetchone()
            return dict(row) if row else None

    # --- Sections ---

    def add_section(self, bill_id: int, text: str, **kwargs) -> int:
        with self.connect() as conn:
            cols = ["bill_id", "text"] + list(kwargs.keys())
            placeholders = ", ".join("?" for _ in cols)
            col_str = ", ".join(cols)
            cur = conn.execute(
                f"INSERT INTO sections ({col_str}) VALUES ({placeholders})",
                (bill_id, text, *kwargs.values()),
            )
            return cur.lastrowid

    def get_sections(self, bill_id: int, version_id: Optional[int] = None) -> list[dict]:
        with self.connect() as conn:
            if version_id:
                rows = conn.execute(
                    "SELECT * FROM sections WHERE bill_id=? AND version_id=? ORDER BY position",
                    (bill_id, version_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM sections WHERE bill_id=? ORDER BY position",
                    (bill_id,),
                ).fetchall()
            return [dict(r) for r in rows]

    # --- Spending Items ---

    def add_spending_item(self, bill_id: int, amount: str, **kwargs) -> int:
        with self.connect() as conn:
            cols = ["bill_id", "amount"] + list(kwargs.keys())
            placeholders = ", ".join("?" for _ in cols)
            col_str = ", ".join(cols)
            cur = conn.execute(
                f"INSERT INTO spending_items ({col_str}) VALUES ({placeholders})",
                (bill_id, amount, *kwargs.values()),
            )
            return cur.lastrowid

    def get_spending(self, bill_id: int) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM spending_items WHERE bill_id=? ORDER BY amount_numeric DESC",
                (bill_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_total_spending(self, bill_id: int) -> float:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(amount_numeric), 0) as total FROM spending_items WHERE bill_id=?",
                (bill_id,),
            ).fetchone()
            return row["total"]

    # --- Legal References ---

    def add_reference(self, bill_id: int, ref_type: str, ref_text: str, **kwargs) -> int:
        with self.connect() as conn:
            cols = ["bill_id", "ref_type", "ref_text"] + list(kwargs.keys())
            placeholders = ", ".join("?" for _ in cols)
            col_str = ", ".join(cols)
            cur = conn.execute(
                f"INSERT INTO legal_references ({col_str}) VALUES ({placeholders})",
                (bill_id, ref_type, ref_text, *kwargs.values()),
            )
            return cur.lastrowid

    def get_references(self, bill_id: int) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM legal_references WHERE bill_id=?", (bill_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    # --- Deadlines ---

    def add_deadline(self, bill_id: int, **kwargs) -> int:
        with self.connect() as conn:
            cols = ["bill_id"] + list(kwargs.keys())
            placeholders = ", ".join("?" for _ in cols)
            col_str = ", ".join(cols)
            cur = conn.execute(
                f"INSERT INTO deadlines ({col_str}) VALUES ({placeholders})",
                (bill_id, *kwargs.values()),
            )
            return cur.lastrowid

    def get_deadlines(self, bill_id: int) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM deadlines WHERE bill_id=?", (bill_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    # --- Entities ---

    def add_entity(self, bill_id: int, name: str, **kwargs) -> int:
        with self.connect() as conn:
            cols = ["bill_id", "name"] + list(kwargs.keys())
            placeholders = ", ".join("?" for _ in cols)
            col_str = ", ".join(cols)
            cur = conn.execute(
                f"INSERT INTO entities ({col_str}) VALUES ({placeholders})",
                (bill_id, name, *kwargs.values()),
            )
            return cur.lastrowid

    def get_entities(self, bill_id: int) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT name, entity_type, role FROM entities WHERE bill_id=?",
                (bill_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    # --- Summaries ---

    def add_summary(self, bill_id: int, summary_text: str, **kwargs) -> int:
        with self.connect() as conn:
            cols = ["bill_id", "summary_text"] + list(kwargs.keys())
            placeholders = ", ".join("?" for _ in cols)
            col_str = ", ".join(cols)
            cur = conn.execute(
                f"INSERT INTO summaries ({col_str}) VALUES ({placeholders})",
                (bill_id, summary_text, *kwargs.values()),
            )
            return cur.lastrowid

    def get_summaries(self, bill_id: int) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM summaries WHERE bill_id=? ORDER BY created_at DESC",
                (bill_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_bill_summary(self, bill_id: int) -> Optional[str]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT summary_text FROM summaries WHERE bill_id=? AND section_id IS NULL ORDER BY created_at DESC LIMIT 1",
                (bill_id,),
            ).fetchone()
            return row["summary_text"] if row else None

    # --- Pork Scores ---

    def add_pork_score(self, bill_id: int, spending_item_id: int, score: int, **kwargs) -> int:
        with self.connect() as conn:
            cols = ["bill_id", "spending_item_id", "score"] + list(kwargs.keys())
            placeholders = ", ".join("?" for _ in cols)
            col_str = ", ".join(cols)
            cur = conn.execute(
                f"INSERT INTO pork_scores ({col_str}) VALUES ({placeholders})",
                (bill_id, spending_item_id, score, *kwargs.values()),
            )
            return cur.lastrowid

    def get_pork_scores(self, bill_id: int) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT ps.*, si.amount, si.purpose, si.recipient
                   FROM pork_scores ps
                   JOIN spending_items si ON ps.spending_item_id = si.id
                   WHERE ps.bill_id=?
                   ORDER BY ps.score DESC""",
                (bill_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_bill_pork_summary(self, bill_id: int) -> dict:
        with self.connect() as conn:
            row = conn.execute(
                """SELECT COUNT(*) as scored_items,
                          AVG(score) as avg_score,
                          MAX(score) as max_score,
                          SUM(CASE WHEN score >= 70 THEN 1 ELSE 0 END) as high_pork_count
                   FROM pork_scores WHERE bill_id=?""",
                (bill_id,),
            ).fetchone()
            return dict(row) if row else {}

    # --- Comparisons ---

    def add_comparison(self, bill_id: int, from_version_id: int, to_version_id: int, **kwargs) -> int:
        with self.connect() as conn:
            cols = ["bill_id", "from_version_id", "to_version_id"] + list(kwargs.keys())
            placeholders = ", ".join("?" for _ in cols)
            col_str = ", ".join(cols)
            cur = conn.execute(
                f"INSERT INTO comparisons ({col_str}) VALUES ({placeholders})",
                (bill_id, from_version_id, to_version_id, *kwargs.values()),
            )
            return cur.lastrowid

    def get_comparison(self, bill_id: int, from_version_id: int, to_version_id: int) -> Optional[dict]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM comparisons WHERE bill_id=? AND from_version_id=? AND to_version_id=?",
                (bill_id, from_version_id, to_version_id),
            ).fetchone()
            return dict(row) if row else None

    # --- Stats ---

    def get_stats(self) -> dict:
        with self.connect() as conn:
            bills = conn.execute("SELECT COUNT(*) as c FROM bills").fetchone()["c"]
            spending = conn.execute("SELECT COUNT(*) as c FROM spending_items").fetchone()["c"]
            total = conn.execute(
                "SELECT COALESCE(SUM(amount_numeric), 0) as t FROM spending_items"
            ).fetchone()["t"]
            scored = conn.execute("SELECT COUNT(*) as c FROM pork_scores").fetchone()["c"]
            return {
                "bills_analyzed": bills,
                "spending_items": spending,
                "total_spending": total,
                "items_scored": scored,
            }

    def clear_bill_data(self, bill_id: int):
        """Remove all analysis data for a bill (keeps bill record)."""
        with self.connect() as conn:
            for table in [
                "pork_scores", "comparisons", "summaries", "entities",
                "deadlines", "legal_references", "spending_items", "sections",
            ]:
                conn.execute(f"DELETE FROM {table} WHERE bill_id=?", (bill_id,))
