import pytest

import db


def test_create_entity_rejects_unknown_type(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    with pytest.raises(ValueError, match="Unknown entity type"):
        db.create_entity("dragon_rider", "Test", {}, "")


def test_create_entity_rejects_empty_name(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    with pytest.raises(ValueError, match="non-empty"):
        db.create_entity("npc", "   ", {}, "")


def test_create_entity_strips_name_whitespace(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    entity_id = db.create_entity("npc", "  Gareth  ", {}, "")
    assert db.get_entity(entity_id)["name"] == "Gareth"


def test_create_entity_rejects_non_dict_fields(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    with pytest.raises(ValueError, match="fields must be an object"):
        db.create_entity("npc", "Gareth", "not a dict", "")


def test_create_entity_rejects_unknown_field_key(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    with pytest.raises(ValueError, match="Unknown field"):
        db.create_entity("npc", "Gareth", {"favorite_color": "blue"}, "")


def test_create_entity_rejects_invalid_select_value(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    with pytest.raises(ValueError, match="must be one of"):
        db.create_entity("npc", "Gareth", {"alignment": "Extremely Good"}, "")


def test_create_entity_rejects_invalid_number_value(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    with pytest.raises(ValueError, match="must be a number"):
        db.create_entity("adventurer", "Mira Thorn", {"level": "five"}, "")


def test_create_entity_accepts_blank_optional_fields(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    entity_id = db.create_entity("npc", "Gareth", {"alignment": "", "role": ""}, "")
    assert db.get_entity(entity_id) is not None


def test_create_entity_rejects_malformed_sheet_type(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    with pytest.raises(ValueError, match="fields\\['sheet'\\] must be an object"):
        db.create_entity("adventurer", "Mira Thorn", {"sheet": "not a dict"}, "")


def test_create_entity_rejects_malformed_active_effects_type(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    with pytest.raises(ValueError, match="active_effects'\\] must be a list"):
        db.create_entity("adventurer", "Mira Thorn", {"active_effects": "not a list"}, "")


def test_quest_objectives_default_to_empty_list(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    quest_id = db.create_entity("quest", "Find the Moon Key", {"status": "Active"}, "")

    assert db.get_entity(quest_id)["fields"]["objectives"] == []


def test_quest_objectives_are_validated_and_normalized(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    quest_id = db.create_entity(
        "quest",
        "Find the Moon Key",
        {"objectives": [{"text": "  Recover the key  ", "done": False}]},
        "",
    )

    assert db.get_entity(quest_id)["fields"]["objectives"] == [
        {"text": "Recover the key", "done": False}
    ]


def test_quest_objectives_reject_malformed_shapes(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    with pytest.raises(ValueError, match="objectives'\\] must be a list"):
        db.create_entity("quest", "Find the Moon Key", {"objectives": "Recover the key"}, "")
    with pytest.raises(ValueError, match="objective text"):
        db.create_entity("quest", "Find the Moon Key", {"objectives": [{"text": "", "done": False}]}, "")
    with pytest.raises(ValueError, match="objective done"):
        db.create_entity("quest", "Find the Moon Key", {"objectives": [{"text": "Recover", "done": "yes"}]}, "")


def test_objectives_are_quest_only(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    with pytest.raises(ValueError, match="only valid for quests"):
        db.create_entity("npc", "Mira Thorn", {"objectives": [{"text": "Recover", "done": False}]}, "")


def test_add_and_toggle_objective(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    quest_id = db.create_entity("quest", "Find the Moon Key", {}, "")

    db.add_objective(quest_id, "Recover the key")
    db.toggle_objective(quest_id, 0)

    assert db.get_entity(quest_id)["fields"]["objectives"] == [
        {"text": "Recover the key", "done": True}
    ]


def test_create_entity_normalizes_sheet_on_write(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    entity_id = db.create_entity("adventurer", "Mira Thorn", {"sheet": {"abilities": {"str": 18}}}, "")
    sheet = db.get_entity(entity_id)["fields"]["sheet"]
    assert sheet["abilities"]["str"] == 18
    assert sheet["abilities"]["dex"] == 10  # filled in by normalize_sheet
    assert sheet["hp_max"] == 10  # default


def test_update_entity_raises_for_missing_id(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    with pytest.raises(ValueError, match="No entity with id"):
        db.update_entity(999, "New Name", {}, "")


def test_update_entity_rejects_empty_name(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    entity_id = db.create_entity("npc", "Gareth", {}, "")
    with pytest.raises(ValueError, match="non-empty"):
        db.update_entity(entity_id, "", {}, "")


def test_update_entity_validates_fields_against_the_entitys_own_type(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    entity_id = db.create_entity("npc", "Gareth", {}, "")
    with pytest.raises(ValueError, match="Unknown field"):
        db.update_entity(entity_id, "Gareth", {"cr": "5"}, "")  # cr is an enemy field, not npc


def test_create_relationship_rejects_unknown_rel_type(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    a = db.create_entity("npc", "A", {}, "")
    b = db.create_entity("npc", "B", {}, "")
    with pytest.raises(ValueError, match="Unknown relationship type"):
        db.create_relationship(a, b, "telepathically bonded to", "")


def test_create_relationship_rejects_missing_from_entity(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    b = db.create_entity("npc", "B", {}, "")
    with pytest.raises(ValueError, match="No entity with id 999"):
        db.create_relationship(999, b, "knows", "")


def test_create_relationship_rejects_missing_to_entity(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    a = db.create_entity("npc", "A", {}, "")
    with pytest.raises(ValueError, match="No entity with id 999"):
        db.create_relationship(a, 999, "knows", "")


def test_replace_all_rejects_unknown_entity_type_without_wiping_existing_data(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    existing_id = db.create_entity("npc", "Existing NPC", {}, "")

    bad_entities = [{
        "id": 1, "type": "dragon_rider", "name": "Bad", "fields": {},
        "notes": "", "created_at": db.now(), "updated_at": db.now(),
    }]
    with pytest.raises(ValueError, match="Unknown entity type"):
        db.replace_all(bad_entities, [])

    assert db.get_entity(existing_id)["name"] == "Existing NPC"


def test_replace_all_rejects_unknown_relationship_type_without_wiping_existing_data(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    existing_id = db.create_entity("npc", "Existing NPC", {}, "")

    entities = [{
        "id": 1, "type": "npc", "name": "A", "fields": {},
        "notes": "", "created_at": db.now(), "updated_at": db.now(),
    }, {
        "id": 2, "type": "npc", "name": "B", "fields": {},
        "notes": "", "created_at": db.now(), "updated_at": db.now(),
    }]
    bad_relationships = [{
        "id": 1, "from_id": 1, "to_id": 2, "rel_type": "telepathically bonded to",
        "notes": "", "created_at": db.now(),
    }]
    with pytest.raises(ValueError, match="Unknown relationship type"):
        db.replace_all(entities, bad_relationships)

    assert db.get_entity(existing_id)["name"] == "Existing NPC"


def test_replace_all_normalizes_sheet_shapes_leniently(monkeypatch, tmp_path):
    """Bulk import stays backward-compatible with older backups: it
    normalizes sub-shapes but doesn't reject unknown flat field keys the
    way create_entity/update_entity do."""
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    entities = [{
        "id": 1, "type": "adventurer", "name": "Mira Thorn",
        "fields": {"deprecated_old_field": "kept as-is", "sheet": {"abilities": {"str": 18}}},
        "notes": "", "created_at": db.now(), "updated_at": db.now(),
    }]
    db.replace_all(entities, [])

    restored = db.get_entity(1)
    assert restored["fields"]["deprecated_old_field"] == "kept as-is"
    assert restored["fields"]["sheet"]["abilities"]["str"] == 18
    assert restored["fields"]["sheet"]["abilities"]["dex"] == 10
