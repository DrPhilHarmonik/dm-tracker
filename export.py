import json
from pathlib import Path
from datetime import datetime

import yaml

import db
from db import list_entities, get_relationships
from models import ENTITY_LABELS, ENTITY_SCHEMAS

BACKUP_FORMAT = "dm-tracker-backup"
BACKUP_VERSION = 1


def slugify(name: str) -> str:
    return name.strip().replace("/", "-").replace("\\", "-")


def wikilink_target(name: str) -> str:
    return str(name).replace("|", "\\|").replace("]", "\\]")


def inline_text(value: object) -> str:
    return str(value).replace("\n", "<br>")


def export_vault(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    all_entities = list_entities()

    counts = {"exported": 0, "dirs": set()}

    for entity in all_entities:
        type_label = ENTITY_LABELS.get(entity["type"], entity["type"].capitalize())
        type_dir = output_dir / type_label
        type_dir.mkdir(exist_ok=True)
        counts["dirs"].add(type_label)

        md = _render_entity(entity)
        file_path = type_dir / f"{slugify(entity['name'])}.md"
        file_path.write_text(md, encoding="utf-8")
        counts["exported"] += 1

    _write_index(output_dir, all_entities)
    return counts["exported"]


def export_json_backup(output_path: Path) -> int:
    output_path = Path(output_path).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    entities = list_entities()
    relationships = db.list_relationships()
    backup = {
        "format": BACKUP_FORMAT,
        "version": BACKUP_VERSION,
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "entities": entities,
        "relationships": relationships,
    }
    output_path.write_text(
        json.dumps(backup, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return len(entities)


def import_json_backup(input_path: Path, *, replace: bool = False) -> dict[str, int]:
    input_path = Path(input_path).expanduser()
    backup = json.loads(input_path.read_text(encoding="utf-8"))
    entities, relationships = _validate_backup(backup)

    if not replace and (list_entities() or db.list_relationships()):
        raise ValueError("Refusing to import into a non-empty database without replace=True")

    db.replace_all(entities, relationships)
    return {"entities": len(entities), "relationships": len(relationships)}


def _validate_backup(backup: dict) -> tuple[list[dict], list[dict]]:
    if backup.get("format") != BACKUP_FORMAT:
        raise ValueError("Unsupported backup format")
    if backup.get("version") != BACKUP_VERSION:
        raise ValueError("Unsupported backup version")

    entities = backup.get("entities")
    relationships = backup.get("relationships")
    if not isinstance(entities, list) or not isinstance(relationships, list):
        raise ValueError("Backup must include entities and relationships lists")

    entity_ids = set()
    normalized_entities = []
    for entity in entities:
        _require_keys(entity, ["id", "type", "name", "fields", "notes", "created_at", "updated_at"], "entity")
        if not isinstance(entity["fields"], dict):
            raise ValueError("Entity fields must be an object")
        entity_id = int(entity["id"])
        if entity_id in entity_ids:
            raise ValueError("Backup contains duplicate entity ids")
        entity_ids.add(entity_id)
        normalized_entities.append({
            "id": entity_id,
            "type": str(entity["type"]),
            "name": str(entity["name"]),
            "fields": entity["fields"],
            "notes": str(entity.get("notes", "")),
            "created_at": str(entity["created_at"]),
            "updated_at": str(entity["updated_at"]),
        })

    normalized_relationships = []
    relationship_ids = set()
    for relationship in relationships:
        _require_keys(relationship, ["id", "from_id", "to_id", "rel_type", "notes", "created_at"], "relationship")
        relationship_id = int(relationship["id"])
        if relationship_id in relationship_ids:
            raise ValueError("Backup contains duplicate relationship ids")
        relationship_ids.add(relationship_id)
        from_id = int(relationship["from_id"])
        to_id = int(relationship["to_id"])
        if from_id not in entity_ids or to_id not in entity_ids:
            raise ValueError("Relationship references a missing entity")
        normalized_relationships.append({
            "id": relationship_id,
            "from_id": from_id,
            "to_id": to_id,
            "rel_type": str(relationship["rel_type"]),
            "notes": str(relationship.get("notes", "")),
            "created_at": str(relationship["created_at"]),
        })

    return normalized_entities, normalized_relationships


def _require_keys(row: dict, keys: list[str], label: str):
    missing = [key for key in keys if key not in row]
    if missing:
        raise ValueError(f"Backup {label} missing required keys: {', '.join(missing)}")


def _render_entity(entity: dict) -> str:
    schema = ENTITY_SCHEMAS.get(entity["type"], [])
    fields = entity["fields"]
    type_label = ENTITY_LABELS.get(entity["type"], entity["type"])

    frontmatter = {
        "type": entity["type"],
        "name": entity["name"],
    }
    for key, label, _, _ in schema:
        val = fields.get(key, "")
        if val:
            frontmatter[key] = val
    frontmatter["created"] = entity["created_at"][:10]
    frontmatter["updated"] = entity["updated_at"][:10]

    lines = ["---"]
    lines.extend(
        yaml.safe_dump(
            frontmatter,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        ).strip().splitlines()
    )
    lines.append("---")
    lines.append("")

    # Title + tag
    lines.append(f"# {entity['name']}")
    lines.append(f"**Type:** {type_label}")
    lines.append("")

    # Structured fields
    structured = [(label, fields.get(key, "")) for key, label, _, _ in schema if fields.get(key, "")]
    if structured:
        lines.append("## Details")
        lines.append("")
        for label, val in structured:
            lines.append(f"- **{label}:** {inline_text(val)}")
        lines.append("")

    # Relationships
    rels = get_relationships(entity["id"])
    if rels:
        lines.append("## Relationships")
        lines.append("")
        for r in rels:
            if r["from_id"] == entity["id"]:
                other_name = r["to_name"]
                direction = r["rel_type"]
            else:
                other_name = r["from_name"]
                direction = f"← {r['rel_type']}"
            wikilink = f"[[{wikilink_target(other_name)}]]"
            note_suffix = f" — {inline_text(r['notes'])}" if r.get("notes") else ""
            lines.append(f"- {direction}: {wikilink}{note_suffix}")
        lines.append("")

    # Notes
    notes = entity.get("notes", "").strip()
    if notes:
        lines.append("## Notes")
        lines.append("")
        lines.append(notes)
        lines.append("")

    return "\n".join(lines)


def _write_index(output_dir: Path, all_entities: list[dict]):
    lines = ["# Campaign Index", ""]
    by_type: dict[str, list] = {}
    for e in all_entities:
        by_type.setdefault(e["type"], []).append(e)

    for type_key, entities in sorted(by_type.items()):
        label = ENTITY_LABELS.get(type_key, type_key)
        lines.append(f"## {label}s")
        lines.append("")
        for e in sorted(entities, key=lambda x: x["name"].lower()):
            lines.append(f"- [[{wikilink_target(e['name'])}]]")
        lines.append("")

    (output_dir / "Index.md").write_text("\n".join(lines), encoding="utf-8")
