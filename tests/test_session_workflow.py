import db
import session_workflow as wf


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()


def test_player_characters_lists_all_adventurers(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    db.create_entity("adventurer", "Brynn Ashforge", {}, "")
    db.create_entity("adventurer", "Yarrow Fenn", {}, "")
    db.create_entity("npc", "Mira Thorn", {}, "")

    names = {e["name"] for e in wf.player_characters()}
    assert names == {"Brynn Ashforge", "Yarrow Fenn"}


def test_active_quests_filters_by_status(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    db.create_entity("quest", "Find the Moon Key", {"status": "Active"}, "")
    db.create_entity("quest", "Old Rumor", {"status": "Rumor"}, "")
    db.create_entity("quest", "Done Deal", {"status": "Complete"}, "")

    names = {e["name"] for e in wf.active_quests()}
    assert names == {"Find the Moon Key"}


def test_active_encounters_includes_planned_and_active(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    db.create_entity("encounter", "Tavern Brawl", {"status": "Planned"}, "")
    db.create_entity("encounter", "Ambush", {"status": "Active"}, "")
    db.create_entity("encounter", "Old Fight", {"status": "Complete"}, "")

    names = {e["name"] for e in wf.active_encounters()}
    assert names == {"Tavern Brawl", "Ambush"}


def test_notable_npcs_related_to_active_quest_or_encounter(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    quest_id = db.create_entity("quest", "Find the Moon Key", {"status": "Active"}, "")
    encounter_id = db.create_entity("encounter", "Ambush", {"status": "Active"}, "")
    npc_a = db.create_entity("npc", "Mira Thorn", {}, "")
    npc_b = db.create_entity("npc", "Dorn Ashvale", {}, "")
    db.create_entity("npc", "Unrelated Cobbler", {}, "")
    db.create_relationship(npc_a, quest_id, "gave quest", "")
    db.create_relationship(encounter_id, npc_b, "involves", "")

    names = {e["name"] for e in wf.notable_npcs()}
    assert names == {"Mira Thorn", "Dorn Ashvale"}


def test_notable_npcs_ignores_inactive_quests_and_encounters(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    quest_id = db.create_entity("quest", "Old Rumor", {"status": "Rumor"}, "")
    npc_id = db.create_entity("npc", "Mira Thorn", {}, "")
    db.create_relationship(npc_id, quest_id, "gave quest", "")

    assert wf.notable_npcs() == []


def test_recent_notes_sorted_newest_first_and_excludes_blank(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    # db.now() only has second resolution, so fake a strictly increasing
    # clock rather than relying on real time between these fast calls.
    ticks = iter(["2026-06-01T10:00:00", "2026-06-01T10:00:01", "2026-06-01T10:00:02"])
    monkeypatch.setattr(db, "now", lambda: next(ticks))

    db.create_entity("npc", "No Notes Here", {}, "")
    db.create_entity("npc", "First", {}, "wrote this first")
    db.create_entity("npc", "Second", {}, "wrote this second")

    notes = wf.recent_notes()
    names = [e["name"] for e in notes]
    assert names[0] == "Second"
    assert "First" in names
    assert "No Notes Here" not in names


def test_recent_notes_respects_limit(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    for i in range(5):
        db.create_entity("npc", f"NPC {i}", {}, f"note {i}")

    assert len(wf.recent_notes(limit=3)) == 3
