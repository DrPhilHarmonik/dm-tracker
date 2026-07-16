import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime

import models
import sheet as sheet_mod
import effects as effects_mod
import combat as combat_mod

DEFAULT_DB_PATH = Path.home() / ".config" / "dm" / "campaign.db"

SPECIAL_FIELD_KEYS = {"sheet", "active_effects", "combat", "objectives"}


def db_path() -> Path:
    configured = os.environ.get("DM_DB_PATH")
    if configured:
        return Path(configured).expanduser()
    return DEFAULT_DB_PATH


def set_db_path(path: str) -> None:
    """Switch the active campaign database at runtime."""
    os.environ["DM_DB_PATH"] = str(path)


def get_conn():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
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


def reset_db():
    with get_conn() as conn:
        conn.execute("DELETE FROM relationships")
        conn.execute("DELETE FROM entities")


def now():
    return datetime.now().isoformat(timespec="seconds")


# --- Validation ---
#
# This module is the single chokepoint every write path goes through --
# live UI/wizard mutations, CLI backup/restore, and vault import all end up
# calling create_entity/update_entity/create_relationship/replace_all.
# Enforcing invariants here protects all of them at once, rather than
# duplicating checks at each call site.

def validate_entity_type(type_: str):
    if type_ not in models.ENTITY_TYPES:
        raise ValueError(f"Unknown entity type: {type_!r}")


def validate_relationship_type(rel_type: str):
    if rel_type not in models.RELATIONSHIP_TYPES:
        raise ValueError(f"Unknown relationship type: {rel_type!r}")


def validate_name(name) -> str:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string")
    return name.strip()


def normalize_objectives(objectives: list) -> list[dict]:
    if not isinstance(objectives, list):
        raise ValueError("fields['objectives'] must be a list")
    normalized = []
    for objective in objectives:
        if not isinstance(objective, dict):
            raise ValueError("each objective must be an object")
        text = objective.get("text", "")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("objective text must be a non-empty string")
        done = objective.get("done", False)
        if not isinstance(done, bool):
            raise ValueError("objective done must be a boolean")
        normalized.append({"text": text.strip(), "done": done})
    return normalized


def objective_progress(fields: dict) -> tuple[int, int]:
    objectives = normalize_objectives(fields.get("objectives", []))
    done = sum(1 for objective in objectives if objective["done"])
    return done, len(objectives)


def normalize_special_fields(fields: dict, type_: str | None = None) -> dict:
    """Type-check and normalize the sheet/active_effects/combat sub-shapes
    that ride alongside an entity's flat schema fields. Used by every write
    path, including bulk import, so malformed nested data can never reach
    the database -- sheet.normalize_sheet() etc. are deliberately lenient
    about missing keys, so this stays backward-compatible with older data."""
    fields = dict(fields)
    if "sheet" in fields:
        if not isinstance(fields["sheet"], dict):
            raise ValueError("fields['sheet'] must be an object")
        fields["sheet"] = sheet_mod.normalize_sheet(fields["sheet"])
    if "active_effects" in fields:
        if not isinstance(fields["active_effects"], list):
            raise ValueError("fields['active_effects'] must be a list")
        fields["active_effects"] = effects_mod.normalize_effects(fields["active_effects"])
    if "combat" in fields:
        if not isinstance(fields["combat"], dict):
            raise ValueError("fields['combat'] must be an object")
        fields["combat"] = combat_mod.normalize_combat(fields["combat"])
    if "objectives" in fields:
        if type_ is not None and type_ != "quest":
            raise ValueError("fields['objectives'] is only valid for quests")
        fields["objectives"] = normalize_objectives(fields["objectives"])
    elif type_ == "quest":
        fields["objectives"] = []
    return fields


def validate_fields(type_: str, fields: dict) -> dict:
    """Strict validation for live create/update: rejects unknown flat field
    keys and out-of-range select/number values for the given entity type,
    then normalizes the sheet/active_effects/combat sub-shapes. Bulk import
    (replace_all) intentionally skips the strict flat-field checks and only
    normalizes the sub-shapes, so restoring an older backup whose schema has
    since changed doesn't fail on fields that were valid when it was taken."""
    if not isinstance(fields, dict):
        raise ValueError("fields must be an object")

    schema = models.ENTITY_SCHEMAS.get(type_, [])
    schema_keys = {key for key, *_ in schema}
    for key in fields:
        if key in SPECIAL_FIELD_KEYS:
            continue
        if key not in schema_keys:
            raise ValueError(f"Unknown field {key!r} for entity type {type_!r}")

    for key, label, ftype, choices in schema:
        if key not in fields:
            continue
        value = fields[key]
        if value in ("", None):
            continue
        if ftype == "select" and choices and value not in choices:
            raise ValueError(f"Invalid value {value!r} for field {label!r}: must be one of {choices}")
        if ftype == "number" and not str(value).strip().lstrip("-").isdigit():
            raise ValueError(f"Invalid value {value!r} for field {label!r}: must be a number")

    return normalize_special_fields(fields, type_)


# --- Entity CRUD ---

def create_entity(type_: str, name: str, fields: dict, notes: str = "") -> int:
    validate_entity_type(type_)
    name = validate_name(name)
    fields = validate_fields(type_, fields)
    ts = now()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO entities (type, name, fields, notes, created_at, updated_at) VALUES (?,?,?,?,?,?)",
            (type_, name, json.dumps(fields), notes, ts, ts),
        )
        return cur.lastrowid


def update_entity(id_: int, name: str, fields: dict, notes: str):
    existing = get_entity(id_)
    if existing is None:
        raise ValueError(f"No entity with id {id_}")
    name = validate_name(name)
    fields = validate_fields(existing["type"], fields)
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


def latest_session() -> dict | None:
    """Return the most recently created session entity, or None."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM entities WHERE type='session' ORDER BY created_at DESC, id DESC LIMIT 1"
        ).fetchone()
        return _row(row)


def search_all(search: str) -> list[dict]:
    like = f"%{search}%"
    sql = (
        "SELECT * FROM entities WHERE name LIKE ? OR notes LIKE ? "
        "ORDER BY name COLLATE NOCASE"
    )
    with get_conn() as conn:
        rows = conn.execute(sql, (like, like)).fetchall()
        return [_row(r) for r in rows]


def _row(row) -> dict | None:
    if row is None:
        return None
    d = dict(row)
    d["fields"] = json.loads(d["fields"])
    return d


# --- Relationship CRUD ---

def create_relationship(from_id: int, to_id: int, rel_type: str, notes: str = "") -> int:
    validate_relationship_type(rel_type)
    if get_entity(from_id) is None:
        raise ValueError(f"No entity with id {from_id}")
    if get_entity(to_id) is None:
        raise ValueError(f"No entity with id {to_id}")
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


def list_relationships() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM relationships ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]


def replace_all(entities: list[dict], relationships: list[dict]):
    # Validate everything before touching the database, so a bad import
    # raises without wiping existing data.
    normalized_entities = []
    for entity in entities:
        validate_entity_type(entity["type"])
        normalized_entities.append({**entity, "fields": normalize_special_fields(entity["fields"], entity["type"])})
    for relationship in relationships:
        validate_relationship_type(relationship["rel_type"])

    with get_conn() as conn:
        conn.execute("DELETE FROM relationships")
        conn.execute("DELETE FROM entities")
        conn.executemany(
            """
            INSERT INTO entities (id, type, name, fields, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    entity["id"],
                    entity["type"],
                    entity["name"],
                    json.dumps(entity["fields"]),
                    entity.get("notes", ""),
                    entity["created_at"],
                    entity["updated_at"],
                )
                for entity in normalized_entities
            ],
        )
        conn.executemany(
            """
            INSERT INTO relationships (id, from_id, to_id, rel_type, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    relationship["id"],
                    relationship["from_id"],
                    relationship["to_id"],
                    relationship["rel_type"],
                    relationship.get("notes", ""),
                    relationship["created_at"],
                )
                for relationship in relationships
            ],
        )


def entity_counts() -> dict[str, int]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT type, COUNT(*) as c FROM entities GROUP BY type"
        ).fetchall()
        return {r["type"]: r["c"] for r in rows}


def add_objective(quest_id: int, text: str) -> None:
    quest = get_entity(quest_id)
    if quest is None:
        raise ValueError(f"No entity with id {quest_id}")
    if quest["type"] != "quest":
        raise ValueError("objectives can only be added to quests")
    fields = dict(quest["fields"])
    objectives = normalize_objectives(fields.get("objectives", []))
    objectives.append({"text": text, "done": False})
    fields["objectives"] = objectives
    update_entity(quest_id, quest["name"], fields, quest["notes"])


def toggle_objective(quest_id: int, index: int) -> None:
    quest = get_entity(quest_id)
    if quest is None:
        raise ValueError(f"No entity with id {quest_id}")
    if quest["type"] != "quest":
        raise ValueError("objectives can only be toggled on quests")
    fields = dict(quest["fields"])
    objectives = normalize_objectives(fields.get("objectives", []))
    if index < 0 or index >= len(objectives):
        raise IndexError("objective index out of range")
    objectives[index]["done"] = not objectives[index]["done"]
    fields["objectives"] = objectives
    update_entity(quest_id, quest["name"], fields, quest["notes"])
