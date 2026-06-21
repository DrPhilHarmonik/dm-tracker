import db


def player_characters() -> list[dict]:
    return db.list_entities("adventurer")


def active_quests() -> list[dict]:
    return [q for q in db.list_entities("quest") if q["fields"].get("status") == "Active"]


def active_encounters() -> list[dict]:
    return [e for e in db.list_entities("encounter") if e["fields"].get("status") in ("Planned", "Active")]


def notable_npcs() -> list[dict]:
    """NPCs related (either direction) to an active quest or active encounter."""
    target_ids = {q["id"] for q in active_quests()} | {e["id"] for e in active_encounters()}
    npc_ids = set()
    for target_id in target_ids:
        for rel in db.get_relationships(target_id):
            if rel["from_id"] == target_id:
                other_id, other_type = rel["to_id"], rel["to_type"]
            else:
                other_id, other_type = rel["from_id"], rel["from_type"]
            if other_type == "npc":
                npc_ids.add(other_id)
    npcs = [db.get_entity(i) for i in npc_ids]
    return sorted(npcs, key=lambda e: e["name"].lower())


def recent_notes(limit: int = 10) -> list[dict]:
    """Any entity with non-empty notes, most recently updated first."""
    noted = [e for e in db.list_entities() if e["notes"].strip()]
    noted.sort(key=lambda e: e["updated_at"], reverse=True)
    return noted[:limit]
