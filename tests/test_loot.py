"""Tests for Phase 30 -- Party Loot Tracker."""
import pytest
import db


@pytest.fixture
def session_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    session_id = db.create_entity("session", "Session 1", {}, "")
    return session_id


# ---------------------------------------------------------------------------
# normalize_loot
# ---------------------------------------------------------------------------

def test_normalize_loot_empty():
    assert db.normalize_loot([]) == []


def test_normalize_loot_basic():
    result = db.normalize_loot([{"name": "Sword", "qty": "1", "value": "15 gp", "owner": ""}])
    assert result == [{"name": "Sword", "qty": "1", "value": "15 gp", "owner": ""}]


def test_normalize_loot_defaults_qty():
    result = db.normalize_loot([{"name": "Potion"}])
    assert result[0]["qty"] == "1"


def test_normalize_loot_strips_whitespace():
    result = db.normalize_loot([{"name": "  Ring  ", "value": " 100 gp "}])
    assert result[0]["name"] == "Ring"
    assert result[0]["value"] == "100 gp"


def test_normalize_loot_raises_on_empty_name():
    with pytest.raises(ValueError, match="name"):
        db.normalize_loot([{"name": ""}])


def test_normalize_loot_raises_on_non_list():
    with pytest.raises(ValueError):
        db.normalize_loot("not a list")


def test_normalize_loot_raises_on_non_dict_entry():
    with pytest.raises(ValueError):
        db.normalize_loot(["not a dict"])


# ---------------------------------------------------------------------------
# Session entity gets empty loot on creation
# ---------------------------------------------------------------------------

def test_session_created_with_empty_loot(session_db):
    session = db.get_entity(session_db)
    assert "loot" in session["fields"]
    assert session["fields"]["loot"] == []


# ---------------------------------------------------------------------------
# add_loot_entry
# ---------------------------------------------------------------------------

def test_add_loot_entry(session_db):
    db.add_loot_entry(session_db, "Longsword", "1", "15 gp")
    session = db.get_entity(session_db)
    assert len(session["fields"]["loot"]) == 1
    entry = session["fields"]["loot"][0]
    assert entry["name"] == "Longsword"
    assert entry["qty"] == "1"
    assert entry["value"] == "15 gp"
    assert entry["owner"] == ""


def test_add_multiple_loot_entries(session_db):
    db.add_loot_entry(session_db, "Shield", "1", "")
    db.add_loot_entry(session_db, "Gold", "3", "30 gp")
    session = db.get_entity(session_db)
    assert len(session["fields"]["loot"]) == 2


def test_add_loot_raises_on_non_session(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    quest_id = db.create_entity("quest", "My Quest", {}, "")
    with pytest.raises(ValueError, match="sessions"):
        db.add_loot_entry(quest_id, "Sword", "1", "")


def test_add_loot_raises_on_missing_id(session_db):
    with pytest.raises(ValueError, match="No entity"):
        db.add_loot_entry(9999, "Sword", "1", "")


# ---------------------------------------------------------------------------
# assign_loot
# ---------------------------------------------------------------------------

def test_assign_loot(session_db):
    db.add_loot_entry(session_db, "Ring of Protection", "1", "")
    db.assign_loot(session_db, 0, "Lyra")
    session = db.get_entity(session_db)
    assert session["fields"]["loot"][0]["owner"] == "Lyra"


def test_assign_loot_empty_string_unassigns(session_db):
    db.add_loot_entry(session_db, "Helm", "1", "")
    db.assign_loot(session_db, 0, "Brynn")
    db.assign_loot(session_db, 0, "")
    session = db.get_entity(session_db)
    assert session["fields"]["loot"][0]["owner"] == ""


def test_assign_loot_raises_on_bad_index(session_db):
    db.add_loot_entry(session_db, "Sword", "1", "")
    with pytest.raises(IndexError):
        db.assign_loot(session_db, 5, "Alice")


# ---------------------------------------------------------------------------
# remove_loot_entry
# ---------------------------------------------------------------------------

def test_remove_loot_entry(session_db):
    db.add_loot_entry(session_db, "Dagger", "1", "")
    db.add_loot_entry(session_db, "Potion", "2", "50 gp")
    db.remove_loot_entry(session_db, 0)
    session = db.get_entity(session_db)
    assert len(session["fields"]["loot"]) == 1
    assert session["fields"]["loot"][0]["name"] == "Potion"


def test_remove_loot_raises_on_bad_index(session_db):
    with pytest.raises(IndexError):
        db.remove_loot_entry(session_db, 0)


# ---------------------------------------------------------------------------
# unassigned_loot
# ---------------------------------------------------------------------------

def test_unassigned_loot_empty(session_db):
    assert db.unassigned_loot() == []


def test_unassigned_loot_returns_unassigned(session_db):
    db.add_loot_entry(session_db, "Staff", "1", "")
    result = db.unassigned_loot()
    assert len(result) == 1
    assert result[0]["name"] == "Staff"
    assert result[0]["session_id"] == session_db
    assert result[0]["session_name"] == "Session 1"


def test_unassigned_loot_excludes_assigned(session_db):
    db.add_loot_entry(session_db, "Sword", "1", "")
    db.add_loot_entry(session_db, "Shield", "1", "")
    db.assign_loot(session_db, 0, "Gorrak")
    result = db.unassigned_loot()
    assert len(result) == 1
    assert result[0]["name"] == "Shield"


def test_unassigned_loot_across_sessions(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    s1 = db.create_entity("session", "Session 1", {}, "")
    s2 = db.create_entity("session", "Session 2", {}, "")
    db.add_loot_entry(s1, "Ring", "1", "")
    db.add_loot_entry(s2, "Wand", "1", "")
    result = db.unassigned_loot()
    assert len(result) == 2
    sessions = {r["session_name"] for r in result}
    assert sessions == {"Session 1", "Session 2"}
