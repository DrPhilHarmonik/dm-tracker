import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path.home() / ".config" / "dm" / "campaign.db"


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                fields TEXT NOT NULL DEFAULT '{}',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
                to_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
                rel_type TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);
            CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
            CREATE INDEX IF NOT EXISTS idx_rel_from ON relationships(from_id);
            CREATE INDEX IF NOT EXISTS idx_rel_to ON relationships(to_id);
        """)


def now():
    return datetime.now().isoformat(timespec="seconds")


# --- Entity CRUD ---

def create_entity(type_: str, name: str, fields: dict, notes: str = "") -> int:
    ts = now()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO entities (type, name, fields, notes, created_at, updated_at) VALUES (?,?,?,?,?,?)",
            (type_, name, json.dumps(fields), notes, ts, ts),
        )
        return cur.lastrowid


def update_entity(id_: int, name: str, fields: dict, notes: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE entities SET name=?, fields=?, notes=?, updated_at=? WHERE id=?",
            (name, json.dumps(fields), notes, now(), id_),
        )


def delete_entity(id_: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM entities WHERE id=?", (id_,))


def get_entity(id_: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM entities WHERE id=?", (id_,)).fetchone()
        return _row(row)


def list_entities(type_: str = None, search: str = None) -> list[dict]:
    sql = "SELECT * FROM entities"
    params = []
    clauses = []
    if type_:
        clauses.append("type=?")
        params.append(type_)
    if search:
        clauses.append("name LIKE ?")
        params.append(f"%{search}%")
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY name COLLATE NOCASE"
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [_row(r) for r in rows]


def _row(row) -> dict | None:
    if row is None:
        return None
    d = dict(row)
    d["fields"] = json.loads(d["fields"])
    return d


# --- Relationship CRUD ---

def create_relationship(from_id: int, to_id: int, rel_type: str, notes: str = "") -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO relationships (from_id, to_id, rel_type, notes, created_at) VALUES (?,?,?,?,?)",
            (from_id, to_id, rel_type, notes, now()),
        )
        return cur.lastrowid


def delete_relationship(id_: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM relationships WHERE id=?", (id_,))


def get_relationships(entity_id: int) -> list[dict]:
    sql = """
        SELECT r.id, r.rel_type, r.notes, r.from_id, r.to_id,
               ef.name as from_name, ef.type as from_type,
               et.name as to_name, et.type as to_type
        FROM relationships r
        JOIN entities ef ON ef.id = r.from_id
        JOIN entities et ON et.id = r.to_id
        WHERE r.from_id=? OR r.to_id=?
        ORDER BY r.rel_type, et.name
    """
    with get_conn() as conn:
        rows = conn.execute(sql, (entity_id, entity_id)).fetchall()
        return [dict(r) for r in rows]


def entity_counts() -> dict[str, int]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT type, COUNT(*) as c FROM entities GROUP BY type"
        ).fetchall()
        return {r["type"]: r["c"] for r in rows}
