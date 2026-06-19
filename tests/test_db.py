import db


def test_entity_crud_and_search(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    entity_id = db.create_entity(
        "npc",
        "Mira Thorn",
        {"race": "Human", "role": "Innkeeper"},
        "Knows the old road.",
    )

    entity = db.get_entity(entity_id)
    assert entity["name"] == "Mira Thorn"
    assert entity["fields"]["role"] == "Innkeeper"
    assert entity["notes"] == "Knows the old road."

    results = db.list_entities("npc", "mira")
    assert [result["id"] for result in results] == [entity_id]

    db.update_entity(
        entity_id,
        "Mira Thorn",
        {"race": "Human", "role": "Guild Contact"},
        "Pays for information.",
    )

    updated = db.get_entity(entity_id)
    assert updated["fields"]["role"] == "Guild Contact"
    assert updated["notes"] == "Pays for information."


def test_search_all_matches_name_or_notes_across_types(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    npc_id = db.create_entity("npc", "Mira Thorn", {}, "Keeps a ledger.")
    loc_id = db.create_entity("location", "Thornwood", {}, "")
    db.create_entity("quest", "Unrelated Quest", {}, "Nothing to do with Mira.")
    db.create_entity("item", "Plain Dagger", {}, "")

    by_name = db.search_all("thorn")
    assert {e["id"] for e in by_name} == {npc_id, loc_id}

    by_notes = db.search_all("ledger")
    assert [e["id"] for e in by_notes] == [npc_id]


def test_delete_entity_cascades_relationships(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    npc_id = db.create_entity("npc", "Mira Thorn", {}, "")
    faction_id = db.create_entity("faction", "Silver Lanterns", {}, "")
    rel_id = db.create_relationship(npc_id, faction_id, "member of", "Secretly.")

    rels = db.get_relationships(npc_id)
    assert [rel["id"] for rel in rels] == [rel_id]

    db.delete_entity(faction_id)

    assert db.get_relationships(npc_id) == []
    assert db.get_entity(faction_id) is None
