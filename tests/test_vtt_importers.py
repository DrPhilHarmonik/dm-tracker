"""Tests for Phase 29 VTT importers: Foundry, Roll20, DDB Encounter."""
import json
from pathlib import Path

import pytest

import db
from importers.foundry import parse_foundry_json
from importers.roll20 import parse_roll20_json
from importers.ddb_encounter import parse_ddb_encounter, import_encounter

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Foundry VTT -- player character
# ---------------------------------------------------------------------------

def test_foundry_pc_name_and_type():
    result = parse_foundry_json(FIXTURES / "sample_foundry_pc.json")
    assert result["name"] == "Theodric the Bold"
    assert result["entity_type"] == "adventurer"


def test_foundry_pc_abilities():
    result = parse_foundry_json(FIXTURES / "sample_foundry_pc.json")
    abilities = result["fields"]["sheet"]["abilities"]
    assert abilities["str"] == 16
    assert abilities["dex"] == 13
    assert abilities["con"] == 15
    assert abilities["int"] == 10
    assert abilities["wis"] == 12
    assert abilities["cha"] == 14


def test_foundry_pc_hp_ac_speed():
    result = parse_foundry_json(FIXTURES / "sample_foundry_pc.json")
    sheet = result["fields"]["sheet"]
    assert sheet["hp_max"] == 45
    assert sheet["hp_current"] == 38
    assert sheet["ac"] == 17
    assert sheet["speed"] == 30


def test_foundry_pc_level_and_flat_fields():
    result = parse_foundry_json(FIXTURES / "sample_foundry_pc.json")
    assert result["fields"]["level"] == 5
    assert result["fields"]["race"] == "Human"
    assert result["fields"]["class_name"] == "Paladin"


def test_foundry_pc_skill_proficiencies():
    result = parse_foundry_json(FIXTURES / "sample_foundry_pc.json")
    skill_profs = result["fields"]["sheet"]["skill_proficiencies"]
    assert skill_profs.get("athletics") == "proficient"
    assert skill_profs.get("perception") == "expertise"


def test_foundry_pc_bio_strips_html():
    result = parse_foundry_json(FIXTURES / "sample_foundry_pc.json")
    assert "<p>" not in result["notes"]
    assert "Tyr" in result["notes"]


# ---------------------------------------------------------------------------
# Foundry VTT -- NPC
# ---------------------------------------------------------------------------

def test_foundry_npc_becomes_enemy():
    result = parse_foundry_json(FIXTURES / "sample_foundry_npc.json")
    assert result["entity_type"] == "enemy"


def test_foundry_npc_cr_fraction():
    result = parse_foundry_json(FIXTURES / "sample_foundry_npc.json")
    assert result["fields"]["cr"] == "1/4"


def test_foundry_npc_creature_type():
    result = parse_foundry_json(FIXTURES / "sample_foundry_npc.json")
    assert result["fields"]["creature_type"] == "Humanoid"


def test_foundry_npc_stats():
    result = parse_foundry_json(FIXTURES / "sample_foundry_npc.json")
    sheet = result["fields"]["sheet"]
    assert sheet["hp_max"] == 7
    assert sheet["ac"] == 15
    assert sheet["abilities"]["dex"] == 14


def test_foundry_raises_on_bad_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not json")
    with pytest.raises(ValueError, match="Could not read JSON"):
        parse_foundry_json(bad)


def test_foundry_raises_on_unrecognized_schema(tmp_path):
    other = tmp_path / "other.json"
    other.write_text(json.dumps({"foo": "bar"}))
    with pytest.raises(ValueError, match="Foundry VTT"):
        parse_foundry_json(other)


# ---------------------------------------------------------------------------
# Roll20
# ---------------------------------------------------------------------------

def test_roll20_name_and_type():
    result = parse_roll20_json(FIXTURES / "sample_roll20.json")
    assert result["name"] == "Brynn Stonehaven"
    assert result["entity_type"] == "adventurer"


def test_roll20_abilities():
    result = parse_roll20_json(FIXTURES / "sample_roll20.json")
    abilities = result["fields"]["sheet"]["abilities"]
    assert abilities["str"] == 17
    assert abilities["dex"] == 13
    assert abilities["con"] == 15
    assert abilities["wis"] == 12


def test_roll20_combat_stats():
    result = parse_roll20_json(FIXTURES / "sample_roll20.json")
    sheet = result["fields"]["sheet"]
    assert sheet["hp_max"] == 52
    assert sheet["hp_current"] == 45
    assert sheet["ac"] == 18
    assert sheet["speed"] == 25


def test_roll20_level_race_class():
    result = parse_roll20_json(FIXTURES / "sample_roll20.json")
    assert result["fields"]["level"] == 5
    assert result["fields"]["race"] == "Mountain Dwarf"
    assert result["fields"]["class_name"] == "Fighter"


def test_roll20_skill_proficiencies():
    result = parse_roll20_json(FIXTURES / "sample_roll20.json")
    skill_profs = result["fields"]["sheet"]["skill_proficiencies"]
    assert skill_profs.get("athletics") == "proficient"
    assert skill_profs.get("perception") == "expertise"


def test_roll20_bio_in_notes():
    result = parse_roll20_json(FIXTURES / "sample_roll20.json")
    assert "northern mountains" in result["notes"]


def test_roll20_accepts_characters_wrapper(tmp_path):
    wrapped = {"characters": [json.loads((FIXTURES / "sample_roll20.json").read_text())]}
    p = tmp_path / "wrapped.json"
    p.write_text(json.dumps(wrapped))
    result = parse_roll20_json(p)
    assert result["name"] == "Brynn Stonehaven"


def test_roll20_raises_on_missing_attribs(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"name": "Bob"}))
    with pytest.raises(ValueError, match="attribs"):
        parse_roll20_json(bad)


def test_roll20_raises_on_bad_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not json")
    with pytest.raises(ValueError, match="Could not read JSON"):
        parse_roll20_json(bad)


# ---------------------------------------------------------------------------
# D&D Beyond Encounter
# ---------------------------------------------------------------------------

def test_ddb_encounter_parse_name():
    result = parse_ddb_encounter(FIXTURES / "sample_ddb_encounter.json")
    assert result["encounter_name"] == "Goblin Ambush"


def test_ddb_encounter_parse_monsters():
    result = parse_ddb_encounter(FIXTURES / "sample_ddb_encounter.json")
    assert len(result["monsters"]) == 3
    names = [m["name"] for m in result["monsters"]]
    assert "Goblin" in names
    assert "Bugbear" in names


def test_ddb_encounter_parse_counts():
    result = parse_ddb_encounter(FIXTURES / "sample_ddb_encounter.json")
    goblin = next(m for m in result["monsters"] if m["name"] == "Goblin")
    assert goblin["count"] == 3


def test_ddb_encounter_srd_lookup():
    result = parse_ddb_encounter(FIXTURES / "sample_ddb_encounter.json")
    goblin = next(m for m in result["monsters"] if m["name"] == "Goblin")
    assert goblin["srd_monster"] is not None
    assert goblin["srd_monster"]["name"] == "Goblin"


def test_ddb_encounter_unknown_monster_is_none():
    result = parse_ddb_encounter(FIXTURES / "sample_ddb_encounter.json")
    xanathar = next(m for m in result["monsters"] if "Xanathar" in m["name"])
    assert xanathar["srd_monster"] is None


def test_ddb_encounter_import_creates_entities(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    parsed = parse_ddb_encounter(FIXTURES / "sample_ddb_encounter.json")
    summary = import_encounter(parsed)
    assert summary["encounter_name"] == "Goblin Ambush"
    assert len(summary["created"]) == 3
    assert "Xanathar the Beholder" in summary["skipped_srd_lookup"]
    encounter = db.get_entity(summary["encounter_id"])
    assert encounter is not None
    assert encounter["type"] == "encounter"
    enemies = db.list_entities("enemy")
    assert len(enemies) == 3


def test_ddb_encounter_links_enemies_to_encounter(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    parsed = parse_ddb_encounter(FIXTURES / "sample_ddb_encounter.json")
    summary = import_encounter(parsed)
    rels = db.get_relationships(summary["encounter_id"])
    assert len(rels) == 3
    assert all(r["rel_type"] == "involves" for r in rels)


def test_ddb_encounter_count_suffix_in_name(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    parsed = parse_ddb_encounter(FIXTURES / "sample_ddb_encounter.json")
    import_encounter(parsed)
    enemies = db.list_entities("enemy")
    names = {e["name"] for e in enemies}
    assert "Goblin (x3)" in names
    assert "Bugbear" in names  # count 1 -- no suffix


def test_ddb_encounter_raises_on_bad_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not json")
    with pytest.raises(ValueError, match="Could not read JSON"):
        parse_ddb_encounter(bad)


def test_ddb_encounter_raises_on_no_monsters(tmp_path):
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"name": "Empty", "monsters": []}))
    with pytest.raises(ValueError, match="No valid monsters"):
        parse_ddb_encounter(empty)


def test_ddb_encounter_accepts_alternate_key_names(tmp_path):
    alt = tmp_path / "alt.json"
    alt.write_text(json.dumps({
        "encounterName": "Orc Raid",
        "creatures": [{"name": "Orc", "count": 4}],
    }))
    result = parse_ddb_encounter(alt)
    assert result["encounter_name"] == "Orc Raid"
    assert result["monsters"][0]["count"] == 4
