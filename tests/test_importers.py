"""Tests for Phase 16 importers: D&D Beyond JSON and CSV."""
import json
from pathlib import Path

import pytest

import db
from importers import import_entity
from importers.ddb import parse_ddb_json
from importers.csv_import import parse_csv, write_template

FIXTURES = Path(__file__).parent / "fixtures"


# -- D&D Beyond JSON importer -------------------------------------------------

def test_ddb_parses_name_and_class(tmp_path):
    result = parse_ddb_json(FIXTURES / "sample_ddb.json")
    assert result["name"] == "Lyra Moonwhisper"
    assert result["entity_type"] == "adventurer"
    assert result["fields"]["class_name"] == "Wizard"


def test_ddb_parses_ability_scores():
    result = parse_ddb_json(FIXTURES / "sample_ddb.json")
    abilities = result["fields"]["sheet"]["abilities"]
    assert abilities["str"] == 8
    assert abilities["dex"] == 14
    assert abilities["con"] == 13
    assert abilities["int"] == 16
    assert abilities["wis"] == 10
    assert abilities["cha"] == 12


def test_ddb_parses_hp_with_damage_taken():
    result = parse_ddb_json(FIXTURES / "sample_ddb.json")
    sheet = result["fields"]["sheet"]
    assert sheet["hp_max"] == 28
    assert sheet["hp_current"] == 23   # 28 - 5 removedHitPoints


def test_ddb_parses_ac_speed_race():
    result = parse_ddb_json(FIXTURES / "sample_ddb.json")
    sheet = result["fields"]["sheet"]
    assert sheet["ac"] == 13
    assert sheet["speed"] == 30
    assert result["fields"]["race"] == "High Elf"


def test_ddb_parses_level():
    result = parse_ddb_json(FIXTURES / "sample_ddb.json")
    assert result["fields"]["level"] == 5
    assert result["fields"]["sheet"]["level"] == 5


def test_ddb_bakes_class_data():
    result = parse_ddb_json(FIXTURES / "sample_ddb.json")
    sheet = result["fields"]["sheet"]
    assert sheet["hit_dice"] == "5d6"
    assert sheet["spellcasting_ability"] == "int"
    assert "light crossbows" in sheet["proficiencies"].lower()


def test_ddb_maps_skill_proficiencies():
    result = parse_ddb_json(FIXTURES / "sample_ddb.json")
    skill_profs = result["fields"]["sheet"]["skill_proficiencies"]
    assert skill_profs.get("arcana") == "proficient"      # id 3, value 1
    assert skill_profs.get("history") == "proficient"     # id 6, value 1
    assert skill_profs.get("religion") == "expertise"     # id 15, value 2


def test_ddb_collects_notes():
    result = parse_ddb_json(FIXTURES / "sample_ddb.json")
    notes = result["notes"]
    assert "Myth Drannor" in notes
    assert "Harpers" in notes
    assert "Zhentarim" in notes
    assert "Knowledge is the greatest treasure" in notes


def test_ddb_handles_data_wrapper():
    result = parse_ddb_json(FIXTURES / "sample_ddb_wrapped.json")
    assert result["name"] == "Gorrak Ironhide"
    assert result["fields"]["class_name"] == "Barbarian"
    assert result["fields"]["sheet"]["abilities"]["str"] == 17
    assert result["fields"]["sheet"]["speed"] == 25


def test_ddb_raises_on_bad_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not json at all")
    with pytest.raises(ValueError, match="Could not read JSON"):
        parse_ddb_json(bad)


def test_ddb_raises_on_unrecognized_schema(tmp_path):
    other = tmp_path / "other.json"
    other.write_text(json.dumps({"foo": "bar"}))
    with pytest.raises(ValueError, match="D&D Beyond"):
        parse_ddb_json(other)


# -- CSV importer -------------------------------------------------------------

def test_csv_parses_adventurer_rows():
    rows = parse_csv(FIXTURES / "sample_import.csv")
    advs = [r for r in rows if r["entity_type"] == "adventurer"]
    assert len(advs) == 2
    names = {r["name"] for r in advs}
    assert "Brynn Ashforge" in names
    assert "Mira Vex" in names


def test_csv_adventurer_abilities_in_sheet():
    rows = parse_csv(FIXTURES / "sample_import.csv")
    brynn = next(r for r in rows if r["name"] == "Brynn Ashforge")
    abilities = brynn["fields"]["sheet"]["abilities"]
    assert abilities["str"] == 15
    assert abilities["dex"] == 14
    assert abilities["cha"] == 8


def test_csv_adventurer_sheet_columns():
    rows = parse_csv(FIXTURES / "sample_import.csv")
    brynn = next(r for r in rows if r["name"] == "Brynn Ashforge")
    sheet = brynn["fields"]["sheet"]
    assert sheet["ac"] == 16
    assert sheet["hp_max"] == 44
    assert sheet["speed"] == 30
    assert sheet["level"] == 5


def test_csv_adventurer_flat_fields():
    rows = parse_csv(FIXTURES / "sample_import.csv")
    brynn = next(r for r in rows if r["name"] == "Brynn Ashforge")
    assert brynn["fields"]["race"] == "Human"
    assert brynn["fields"]["class_name"] == "Fighter"
    assert brynn["fields"]["level"] == 5


def test_csv_enemy_row():
    rows = parse_csv(FIXTURES / "sample_import.csv")
    goblin = next(r for r in rows if r["name"] == "Goblin Boss")
    assert goblin["entity_type"] == "enemy"
    sheet = goblin["fields"]["sheet"]
    assert sheet["ac"] == 15
    assert sheet["hp_max"] == 21
    assert goblin["fields"]["cr"] == "1"


def test_csv_npc_row():
    rows = parse_csv(FIXTURES / "sample_import.csv")
    mira = next(r for r in rows if r["name"] == "Mira the Innkeeper")
    assert mira["entity_type"] == "npc"
    assert mira["fields"].get("role") == "Innkeeper"
    assert mira["fields"].get("alignment") == "Neutral Good"
    assert "sheet" not in mira["fields"]


def test_csv_location_row():
    rows = parse_csv(FIXTURES / "sample_import.csv")
    saltmarsh = next(r for r in rows if r["name"] == "Saltmarsh")
    assert saltmarsh["entity_type"] == "location"
    assert saltmarsh["notes"] == "Fishing town on the coast"


def test_csv_skips_invalid_type_rows(tmp_path):
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("name,type,notes\nValid NPC,npc,\nBad Entity,wizard,\n,npc,no name\n")
    rows = parse_csv(csv_path)
    assert len(rows) == 1
    assert rows[0]["name"] == "Valid NPC"


def test_csv_template_is_valid_csv(tmp_path):
    tmpl = tmp_path / "template.csv"
    write_template(tmpl)
    rows = parse_csv(tmpl)
    assert len(rows) >= 2
    types = {r["entity_type"] for r in rows}
    assert "adventurer" in types


# -- import_entity shared function --------------------------------------------

def test_import_entity_creates_new(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    result = import_entity("Lyra", "adventurer", {"sheet": {}}, "test notes")
    assert result["entity_id"] is not None
    assert result["warning"] == ""
    entity = db.get_entity(result["entity_id"])
    assert entity["name"] == "Lyra"


def test_import_entity_warns_on_duplicate(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    import_entity("Lyra", "adventurer", {}, "")
    result = import_entity("Lyra", "adventurer", {}, "")
    assert "already exists" in result["warning"]
    # Still created -- additive policy
    assert len(db.list_entities("adventurer")) == 2


def test_import_entity_never_overwrites(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    db.create_entity("adventurer", "Gorrak", {"level": 3}, "original")
    import_entity("Gorrak", "adventurer", {"level": 5}, "imported")
    all_adventurers = db.list_entities("adventurer")
    assert len(all_adventurers) == 2
    # Original still exists untouched
    original = next(e for e in all_adventurers if e["notes"] == "original")
    assert original["fields"].get("level") == 3
