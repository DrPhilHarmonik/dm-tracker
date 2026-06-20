import json

import pytest
import yaml

import db
import export


def test_export_vault_writes_entities_relationships_and_index(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    npc_id = db.create_entity(
        "npc",
        "Mira Thorn",
        {"race": "Human", "role": "Innkeeper"},
        "Keeps a ledger behind the bar.",
    )
    quest_id = db.create_entity(
        "quest",
        "Find the Moon Key",
        {"status": "Active", "giver": "Mira Thorn"},
        "",
    )
    db.create_relationship(npc_id, quest_id, "gave quest", "Payment on return.")

    output_dir = tmp_path / "vault"
    count = export.export_vault(output_dir)

    assert count == 2

    npc_file = output_dir / "NPC" / "Mira Thorn.md"
    quest_file = output_dir / "Quest" / "Find the Moon Key.md"
    index_file = output_dir / "Index.md"

    assert npc_file.exists()
    assert quest_file.exists()
    assert index_file.exists()

    npc_text = npc_file.read_text(encoding="utf-8")
    assert "type: npc" in npc_text
    assert "# Mira Thorn" in npc_text
    assert "- **Role / Title:** Innkeeper" in npc_text
    assert "- gave quest: [[Find the Moon Key]]" in npc_text
    assert "Keeps a ledger behind the bar." in npc_text

    index_text = index_file.read_text(encoding="utf-8")
    assert "- [[Mira Thorn]]" in index_text
    assert "- [[Find the Moon Key]]" in index_text


def test_slugify_replaces_path_separators():
    assert export.slugify("Temple/Lower\\Vault") == "Temple-Lower-Vault"


def test_markdown_export_writes_valid_yaml_for_special_values(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    npc_id = db.create_entity(
        "npc",
        'Mira "The Thorn": West',
        {
            "race": "Half-Elf: Moon Court",
            "role": 'Keeper of "Old Roads"\nSecret broker',
        },
        "First line\nSecond line",
    )
    location_id = db.create_entity(
        "location",
        "Inn ] With | Pipes",
        {"location_type": "Inn / Tavern"},
        "",
    )
    db.create_relationship(npc_id, location_id, "lives in", "Room 3\nBack stairs")

    output_dir = tmp_path / "vault"
    export.export_vault(output_dir)

    md_path = output_dir / "NPC" / 'Mira "The Thorn": West.md'
    text = md_path.read_text(encoding="utf-8")
    frontmatter = yaml.safe_load(text.split("---", 2)[1])

    assert frontmatter["name"] == 'Mira "The Thorn": West'
    assert frontmatter["race"] == "Half-Elf: Moon Court"
    assert frontmatter["role"] == 'Keeper of "Old Roads"\nSecret broker'
    assert "- **Role / Title:** Keeper of \"Old Roads\"<br>Secret broker" in text
    assert "[[Inn \\] With \\| Pipes]]" in text
    assert "Room 3<br>Back stairs" in text

    index_text = (output_dir / "Index.md").read_text(encoding="utf-8")
    assert "[[Inn \\] With \\| Pipes]]" in index_text


def test_json_backup_round_trips_entities_and_relationships(monkeypatch, tmp_path):
    source_db = tmp_path / "source.db"
    monkeypatch.setenv("DM_DB_PATH", str(source_db))
    db.init_db()

    npc_id = db.create_entity(
        "npc",
        "Mira Thorn",
        {"race": "Human", "role": "Innkeeper"},
        "Keeps a ledger behind the bar.",
    )
    faction_id = db.create_entity(
        "faction",
        "Silver Lanterns",
        {"power_level": "Minor"},
        "Local informants.",
    )
    db.create_relationship(npc_id, faction_id, "member of", "Secretly.")

    backup_path = tmp_path / "backup.json"
    count = export.export_json_backup(backup_path)
    assert count == 2

    backup = json.loads(backup_path.read_text(encoding="utf-8"))
    assert backup["format"] == export.BACKUP_FORMAT
    assert backup["version"] == export.BACKUP_VERSION
    assert len(backup["entities"]) == 2
    assert len(backup["relationships"]) == 1

    restore_db = tmp_path / "restore.db"
    monkeypatch.setenv("DM_DB_PATH", str(restore_db))
    db.init_db()

    result = export.import_json_backup(backup_path)

    assert result == {"entities": 2, "relationships": 1}
    restored_npc = db.get_entity(npc_id)
    assert restored_npc["name"] == "Mira Thorn"
    assert restored_npc["fields"]["role"] == "Innkeeper"
    assert restored_npc["notes"] == "Keeps a ledger behind the bar."
    assert db.get_relationships(npc_id)[0]["to_name"] == "Silver Lanterns"


def test_json_import_refuses_non_empty_database_without_replace(monkeypatch, tmp_path):
    source_db = tmp_path / "source.db"
    monkeypatch.setenv("DM_DB_PATH", str(source_db))
    db.init_db()
    db.create_entity("npc", "Mira Thorn", {}, "")
    backup_path = tmp_path / "backup.json"
    export.export_json_backup(backup_path)

    target_db = tmp_path / "target.db"
    monkeypatch.setenv("DM_DB_PATH", str(target_db))
    db.init_db()
    existing_id = db.create_entity("npc", "Existing NPC", {}, "")

    with pytest.raises(ValueError, match="non-empty database"):
        export.import_json_backup(backup_path)

    assert db.get_entity(existing_id)["name"] == "Existing NPC"

    result = export.import_json_backup(backup_path, replace=True)
    assert result == {"entities": 1, "relationships": 0}
    assert db.list_entities()[0]["name"] == "Mira Thorn"


def test_json_import_rejects_missing_relationship_target(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    backup_path = tmp_path / "broken.json"
    backup_path.write_text(
        json.dumps({
            "format": export.BACKUP_FORMAT,
            "version": export.BACKUP_VERSION,
            "entities": [
                {
                    "id": 1,
                    "type": "npc",
                    "name": "Mira Thorn",
                    "fields": {},
                    "notes": "",
                    "created_at": "2026-06-15T10:00:00",
                    "updated_at": "2026-06-15T10:00:00",
                }
            ],
            "relationships": [
                {
                    "id": 1,
                    "from_id": 1,
                    "to_id": 999,
                    "rel_type": "knows",
                    "notes": "",
                    "created_at": "2026-06-15T10:00:00",
                }
            ],
        }),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing entity"):
        export.import_json_backup(backup_path)


def test_export_vault_includes_stats_by_default(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    adv_id = db.create_entity("adventurer", "Mira Thorn", {"race": "Half-Elf"}, "")
    db.update_entity(adv_id, "Mira Thorn", {
        "race": "Half-Elf",
        "sheet": {"abilities": {"str": 12, "dex": 18, "con": 14, "int": 10, "wis": 10, "cha": 10}, "ac": 15},
        "active_effects": [{"source": "Potion of Speed", "stat": "dex", "modifier": 2, "rounds_remaining": 3}],
    }, "")

    output_dir = tmp_path / "vault"
    export.export_vault(output_dir, include_stats=True)
    text = (output_dir / "Adventurer" / "Mira Thorn.md").read_text(encoding="utf-8")

    assert "sheet:" in text
    assert "active_effects:" in text
    assert "## Character Sheet" in text
    assert "DEX 20 (+5)" in text  # effective (buffed) value shown in prose
    assert "Potion of Speed" in text


def test_export_vault_can_exclude_stats(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    adv_id = db.create_entity("adventurer", "Mira Thorn", {"race": "Half-Elf"}, "")
    db.update_entity(adv_id, "Mira Thorn", {
        "race": "Half-Elf",
        "sheet": {"abilities": {"str": 14, "dex": 14, "con": 14, "int": 14, "wis": 14, "cha": 14}},
    }, "")

    output_dir = tmp_path / "vault"
    export.export_vault(output_dir, include_stats=False)
    text = (output_dir / "Adventurer" / "Mira Thorn.md").read_text(encoding="utf-8")

    assert "sheet:" not in text
    assert "## Character Sheet" not in text
    assert "- **Race:** Half-Elf" in text


def test_vault_round_trips_entities_sheets_effects_and_relationships(monkeypatch, tmp_path):
    source_db = tmp_path / "source.db"
    monkeypatch.setenv("DM_DB_PATH", str(source_db))
    db.init_db()

    adv_id = db.create_entity("adventurer", "Mira Thorn", {"race": "Half-Elf", "class_name": "Rogue"},
                               "A sharp-eyed rogue.\nSecond line.")
    db.update_entity(adv_id, "Mira Thorn", {
        "race": "Half-Elf", "class_name": "Rogue",
        "sheet": {
            "abilities": {"str": 12, "dex": 18, "con": 14, "int": 10, "wis": 10, "cha": 10},
            "ac": 15, "hp_max": 32, "hp_current": 32,
            "attacks": [{"name": "Shortsword", "bonus": 7, "damage": "1d6+4", "damage_type": "piercing"}],
            "saving_throw_proficiencies": ["dex"],
            "skill_proficiencies": {"stealth": "expertise"},
        },
        "active_effects": [{"source": "Potion of Speed", "stat": "dex", "modifier": 2, "rounds_remaining": 3}],
    }, "A sharp-eyed rogue.\nSecond line.")
    loc_id = db.create_entity("location", "Dockside Tavern", {"location_type": "Inn / Tavern"}, "")
    db.create_relationship(adv_id, loc_id, "lives in", "Has a back room.\nReserved nightly.")

    vault_dir = tmp_path / "vault"
    export.export_vault(vault_dir, include_stats=True)

    target_db = tmp_path / "target.db"
    monkeypatch.setenv("DM_DB_PATH", str(target_db))
    db.init_db()
    result = export.import_vault(vault_dir)

    assert result == {"entities": 2, "relationships": 1}

    mira = db.list_entities("adventurer")[0]
    assert mira["name"] == "Mira Thorn"
    assert mira["notes"] == "A sharp-eyed rogue.\nSecond line."
    assert mira["fields"]["sheet"]["abilities"]["dex"] == 18  # base value, not the buffed prose value
    assert mira["fields"]["sheet"]["attacks"][0]["name"] == "Shortsword"
    assert mira["fields"]["active_effects"][0]["source"] == "Potion of Speed"

    rels = db.get_relationships(mira["id"])
    assert len(rels) == 1
    assert rels[0]["rel_type"] == "lives in"
    assert rels[0]["to_name"] == "Dockside Tavern"
    assert rels[0]["notes"] == "Has a back room.\nReserved nightly."


def test_vault_import_refuses_non_empty_database_without_replace(monkeypatch, tmp_path):
    source_db = tmp_path / "source.db"
    monkeypatch.setenv("DM_DB_PATH", str(source_db))
    db.init_db()
    db.create_entity("npc", "Mira Thorn", {}, "")
    vault_dir = tmp_path / "vault"
    export.export_vault(vault_dir)

    target_db = tmp_path / "target.db"
    monkeypatch.setenv("DM_DB_PATH", str(target_db))
    db.init_db()
    existing_id = db.create_entity("npc", "Existing NPC", {}, "")

    with pytest.raises(ValueError, match="non-empty database"):
        export.import_vault(vault_dir)

    assert db.get_entity(existing_id)["name"] == "Existing NPC"

    result = export.import_vault(vault_dir, replace=True)
    assert result == {"entities": 1, "relationships": 0}
    assert db.list_entities()[0]["name"] == "Mira Thorn"


def test_vault_import_rejects_missing_frontmatter(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    (vault_dir / "broken.md").write_text("# No frontmatter here\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing YAML frontmatter"):
        export.import_vault(vault_dir)


def test_vault_import_rejects_unknown_entity_type(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    (vault_dir / "broken.md").write_text(
        "---\ntype: dragon_rider\nname: Test\n---\n\n# Test\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match="unknown entity type"):
        export.import_vault(vault_dir)


def test_vault_import_raises_when_directory_has_no_entity_files(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    empty_dir = tmp_path / "empty_vault"
    empty_dir.mkdir()

    with pytest.raises(ValueError, match="No entity files"):
        export.import_vault(empty_dir)


def test_vault_round_trip_preserves_encounter_combatant_identity(monkeypatch, tmp_path):
    """Regression: vault re-import reassigns entity ids sequentially, so a
    raw entity_id inside combat.combatants would silently point at the
    wrong entity after re-import unless it's resolved by name like
    relationships are."""
    source_db = tmp_path / "source.db"
    monkeypatch.setenv("DM_DB_PATH", str(source_db))
    db.init_db()

    adv_id = db.create_entity("adventurer", "Mira Thorn", {}, "")
    enemy_id = db.create_entity("enemy", "Goblin Boss", {}, "")
    # an unrelated entity that sorts between the others alphabetically, so a
    # naive sequential id reassignment on import would silently shift
    # the combatant references onto it if name-based resolution were broken
    db.create_entity("item", "Dagger", {}, "")
    enc_id = db.create_entity("encounter", "Tavern Brawl", {
        "combat": {
            "round": 1, "turn_index": 0, "started": False,
            "combatants": [
                {"entity_id": adv_id, "initiative": 15, "conditions": []},
                {"entity_id": enemy_id, "initiative": 10, "conditions": []},
            ],
        },
    }, "")

    vault_dir = tmp_path / "vault"
    export.export_vault(vault_dir, include_stats=True)

    target_db = tmp_path / "target.db"
    monkeypatch.setenv("DM_DB_PATH", str(target_db))
    db.init_db()
    export.import_vault(vault_dir)

    restored_encounter = db.list_entities("encounter")[0]
    combatants = restored_encounter["fields"]["combat"]["combatants"]
    names = {db.get_entity(c["entity_id"])["name"] for c in combatants}
    assert names == {"Mira Thorn", "Goblin Boss"}
