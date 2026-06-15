from pathlib import Path
from db import list_entities, get_relationships, entity_counts
from models import ENTITY_LABELS, ENTITY_SCHEMAS


def slugify(name: str) -> str:
    return name.strip().replace("/", "-").replace("\\", "-")


def export_vault(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build name->entity map for wikilink resolution
    all_entities = list_entities()
    name_map = {e["name"]: e for e in all_entities}

    counts = {"exported": 0, "dirs": set()}

    for entity in all_entities:
        type_label = ENTITY_LABELS.get(entity["type"], entity["type"].capitalize())
        type_dir = output_dir / type_label
        type_dir.mkdir(exist_ok=True)
        counts["dirs"].add(type_label)

        md = _render_entity(entity, name_map)
        file_path = type_dir / f"{slugify(entity['name'])}.md"
        file_path.write_text(md, encoding="utf-8")
        counts["exported"] += 1

    _write_index(output_dir, all_entities)
    return counts["exported"]


def _render_entity(entity: dict, name_map: dict) -> str:
    schema = ENTITY_SCHEMAS.get(entity["type"], [])
    fields = entity["fields"]
    type_label = ENTITY_LABELS.get(entity["type"], entity["type"])

    lines = []

    # YAML frontmatter
    lines.append("---")
    lines.append(f'type: {entity["type"]}')
    lines.append(f'name: "{entity["name"]}"')
    for key, label, _, _ in schema:
        val = fields.get(key, "")
        if val:
            lines.append(f'{key}: "{val}"')
    lines.append(f'created: {entity["created_at"][:10]}')
    lines.append(f'updated: {entity["updated_at"][:10]}')
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
            lines.append(f"- **{label}:** {val}")
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
            wikilink = f"[[{other_name}]]"
            note_suffix = f" — {r['notes']}" if r.get("notes") else ""
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
            lines.append(f"- [[{e['name']}]]")
        lines.append("")

    (output_dir / "Index.md").write_text("\n".join(lines), encoding="utf-8")
