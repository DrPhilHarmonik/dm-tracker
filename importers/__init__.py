"""Character and entity importers.

All format-specific parsers return the same intermediate dict shape:
    {"name": str, "entity_type": str, "fields": dict, "notes": str}

Pass that to import_entity() to persist it.
"""
import db


def import_entity(name: str, entity_type: str, fields: dict, notes: str = "") -> dict:
    """Create a new entity from imported data.

    Always additive -- never overwrites an existing entity, even if names match.
    Returns {"entity_id": int, "warning": str}.
    """
    existing = [e for e in db.list_entities(entity_type) if e["name"] == name]
    warning = f"An entity named '{name}' already exists as {entity_type}" if existing else ""
    entity_id = db.create_entity(entity_type, name, fields, notes)
    return {"entity_id": entity_id, "warning": warning}
