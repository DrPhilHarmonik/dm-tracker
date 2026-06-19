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
