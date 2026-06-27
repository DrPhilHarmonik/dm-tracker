"""Campaign registry: tracks named campaign DB files in a central manager DB.

The manager DB lives at ~/.local/share/dm_tracker/campaigns.db (separate from
any campaign file). Campaign files default to the same directory.

DM_DB_PATH env var bypasses all of this -- the app opens that file directly.
"""
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

MANAGER_DIR = Path.home() / ".local" / "share" / "dm_tracker"
MANAGER_DB_PATH = MANAGER_DIR / "campaigns.db"
CAMPAIGNS_DIR = MANAGER_DIR / "campaigns"


def _conn():
    MANAGER_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(MANAGER_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_manager() -> None:
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                path        TEXT NOT NULL UNIQUE,
                created_at  TEXT NOT NULL,
                last_opened_at TEXT NOT NULL
            )
        """)
        conn.commit()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def list_campaigns() -> list[dict]:
    """Return all campaigns, most recently opened first."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM campaigns ORDER BY last_opened_at DESC, id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def create_campaign(name: str, path: str | None = None) -> dict:
    """Create a new campaign DB file entry and register it."""
    CAMPAIGNS_DIR.mkdir(parents=True, exist_ok=True)
    if path is None:
        safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in name).strip()
        safe_name = safe_name.replace(" ", "_").lower() or "campaign"
        base = CAMPAIGNS_DIR / f"{safe_name}.db"
        counter = 0
        candidate = base
        while candidate.exists():
            counter += 1
            candidate = CAMPAIGNS_DIR / f"{safe_name}_{counter}.db"
        path = str(candidate)
    now = _now()
    with _conn() as conn:
        cursor = conn.execute(
            "INSERT INTO campaigns (name, path, created_at, last_opened_at) VALUES (?, ?, ?, ?)",
            (name, path, now, now),
        )
        campaign_id = cursor.lastrowid
        conn.commit()
    return get_campaign(campaign_id)


def get_campaign(campaign_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
    return dict(row) if row else None


def open_campaign(campaign_id: int) -> str:
    """Mark as last opened and return the campaign's DB path."""
    with _conn() as conn:
        conn.execute(
            "UPDATE campaigns SET last_opened_at = ? WHERE id = ?",
            (_now(), campaign_id),
        )
        conn.commit()
    campaign = get_campaign(campaign_id)
    return campaign["path"] if campaign else ""


def rename_campaign(campaign_id: int, new_name: str) -> None:
    with _conn() as conn:
        conn.execute("UPDATE campaigns SET name = ? WHERE id = ?", (new_name, campaign_id))
        conn.commit()


def delete_campaign(campaign_id: int, delete_file: bool = False) -> None:
    campaign = get_campaign(campaign_id)
    if not campaign:
        return
    if delete_file:
        try:
            Path(campaign["path"]).unlink(missing_ok=True)
        except OSError:
            pass
    with _conn() as conn:
        conn.execute("DELETE FROM campaigns WHERE id = ?", (campaign_id,))
        conn.commit()


def register_existing(name: str, path: str) -> dict:
    """Register an existing DB file as a named campaign."""
    now = _now()
    with _conn() as conn:
        conn.execute(
            """INSERT INTO campaigns (name, path, created_at, last_opened_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(path) DO UPDATE SET name=excluded.name""",
            (name, path, now, now),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM campaigns WHERE path = ?", (path,)).fetchone()
    return dict(row)


def current_name() -> str:
    """Return the display name for the currently open campaign DB."""
    import db as db_mod
    current_path = str(db_mod.db_path().resolve())
    with _conn() as conn:
        row = conn.execute(
            "SELECT name FROM campaigns WHERE path = ?", (current_path,)
        ).fetchone()
    if row:
        return row["name"]
    # Fallback: just the filename stem
    return Path(current_path).stem


def entity_count_for(path: str) -> int:
    """Count entities in a campaign file without touching the active connection."""
    try:
        conn = sqlite3.connect(path)
        row = conn.execute("SELECT COUNT(*) FROM entities").fetchone()
        conn.close()
        return row[0] if row else 0
    except Exception:
        return 0


def ensure_default() -> str:
    """Ensure at least one campaign exists; return the path to open.

    Called at startup when DM_DB_PATH is not set. If no campaigns are
    registered yet, creates 'My Campaign' automatically.
    """
    init_manager()
    campaigns = list_campaigns()
    if campaigns:
        path = open_campaign(campaigns[0]["id"])
        return path
    campaign = create_campaign("My Campaign")
    return campaign["path"]
