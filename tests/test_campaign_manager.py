"""Tests for the campaign manager (registry DB and campaign lifecycle)."""
import os
from pathlib import Path

import pytest
import campaign_manager as cm
import db


@pytest.fixture(autouse=True)
def isolated_manager(tmp_path, monkeypatch):
    """Redirect manager DB and campaigns dir to tmp_path for isolation."""
    monkeypatch.setattr(cm, "MANAGER_DIR", tmp_path / "dm_tracker")
    monkeypatch.setattr(cm, "MANAGER_DB_PATH", tmp_path / "dm_tracker" / "campaigns.db")
    monkeypatch.setattr(cm, "CAMPAIGNS_DIR", tmp_path / "dm_tracker" / "campaigns")
    cm.init_manager()


def test_init_manager_creates_db(tmp_path):
    assert (tmp_path / "dm_tracker" / "campaigns.db").exists()


def test_list_campaigns_empty():
    assert cm.list_campaigns() == []


def test_create_campaign_registers_and_returns_dict():
    c = cm.create_campaign("Test Campaign")
    assert c["name"] == "Test Campaign"
    assert c["id"] is not None
    assert Path(c["path"]).parent.exists()


def test_create_campaign_auto_names_file():
    c = cm.create_campaign("My Adventure")
    assert "my_adventure" in c["path"]


def test_list_campaigns_returns_most_recent_first():
    cm.create_campaign("Alpha")
    cm.create_campaign("Beta")
    campaigns = cm.list_campaigns()
    assert len(campaigns) == 2
    # Both were just created; Beta was created last so opened last
    assert campaigns[0]["name"] == "Beta"


def test_open_campaign_returns_path_and_updates_timestamp():
    c = cm.create_campaign("A Campaign")
    old_ts = c["last_opened_at"]
    import time; time.sleep(0.01)
    path = cm.open_campaign(c["id"])
    assert path == c["path"]
    updated = cm.get_campaign(c["id"])
    assert updated["last_opened_at"] >= old_ts


def test_rename_campaign():
    c = cm.create_campaign("Old Name")
    cm.rename_campaign(c["id"], "New Name")
    updated = cm.get_campaign(c["id"])
    assert updated["name"] == "New Name"


def test_delete_campaign_removes_from_list():
    c = cm.create_campaign("Doomed")
    cm.delete_campaign(c["id"], delete_file=False)
    assert cm.get_campaign(c["id"]) is None
    assert all(x["name"] != "Doomed" for x in cm.list_campaigns())


def test_delete_campaign_can_remove_file(tmp_path):
    c = cm.create_campaign("To Delete")
    Path(c["path"]).touch()
    assert Path(c["path"]).exists()
    cm.delete_campaign(c["id"], delete_file=True)
    assert not Path(c["path"]).exists()


def test_register_existing(tmp_path):
    fake_db = tmp_path / "legacy.db"
    fake_db.touch()
    c = cm.register_existing("Legacy Campaign", str(fake_db))
    assert c["name"] == "Legacy Campaign"
    assert c["path"] == str(fake_db)
    assert len(cm.list_campaigns()) == 1


def test_register_existing_updates_name_on_conflict(tmp_path):
    fake_db = tmp_path / "legacy.db"
    fake_db.touch()
    cm.register_existing("Old Name", str(fake_db))
    cm.register_existing("New Name", str(fake_db))
    campaigns = cm.list_campaigns()
    assert len(campaigns) == 1
    assert campaigns[0]["name"] == "New Name"


def test_entity_count_for_returns_zero_for_empty(tmp_path):
    path = tmp_path / "empty.db"
    monkeypatch = None  # not needed here
    assert cm.entity_count_for(str(path)) == 0


def test_entity_count_for_counts_real_entities(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    db.create_entity("npc", "Bob", {}, "")
    db.create_entity("npc", "Alice", {}, "")
    count = cm.entity_count_for(str(tmp_path / "test.db"))
    assert count == 2


def test_ensure_default_creates_campaign_when_none_exist():
    path = cm.ensure_default()
    assert path
    assert len(cm.list_campaigns()) == 1
    assert cm.list_campaigns()[0]["name"] == "My Campaign"


def test_ensure_default_opens_existing_if_present():
    c = cm.create_campaign("Existing")
    path = cm.ensure_default()
    assert path == c["path"]
    assert len(cm.list_campaigns()) == 1


def test_set_db_path_changes_active_db(monkeypatch, tmp_path):
    db_a = str(tmp_path / "a.db")
    db.set_db_path(db_a)
    assert str(db.db_path()) == db_a


def test_current_name_returns_campaign_name(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "my_camp.db"))
    db_path_str = str(tmp_path / "my_camp.db")
    cm.register_existing("The Great Campaign", db_path_str)
    db.set_db_path(db_path_str)
    name = cm.current_name()
    assert name == "The Great Campaign"


def test_current_name_falls_back_to_stem(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "strahd_run.db"))
    db.set_db_path(str(tmp_path / "strahd_run.db"))
    name = cm.current_name()
    assert name == "strahd_run"
