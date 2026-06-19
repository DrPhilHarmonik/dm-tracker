import json
import re
from pathlib import Path
from datetime import datetime

import yaml

import db
from db import list_entities, get_relationships
from models import ENTITY_LABELS, ENTITY_SCHEMAS, ENTITY_TYPES
import sheet as shm
import effects as fx

BACKUP_FORMAT = "dm-tracker-backup"
BACKUP_VERSION = 1

# Frontmatter keys that aren't flat schema fields -- handled separately on
# both export and import.
_NON_SCHEMA_KEYS = {"type", "name", "sheet", "active_effects", "combat", "created", "updated"}


def slugify(name: str) -> str:
    return name.strip().replace("/", "-").replace("\\", "-")


def wikilink_target(name: str) -> str:
    return str(name).replace("|", "\\|").replace("]", "\\]")


def inline_text(value: object) -> str:
    return str(value).replace("\n", "<br>")


def export_vault(output_dir: Path, include_stats: bool = True) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)

    all_entities = list_entities()

    exported = 0

    for entity in all_entities:
        type_label = ENTITY_LABELS.get(entity["type"], entity["type"].capitalize())
        type_dir = output_dir / type_label
        type_dir.mkdir(exist_ok=True)

        md = _render_entity(entity, include_stats=include_stats)
        file_path = type_dir / f"{slugify(entity['name'])}.md"
        file_path.write_text(md, encoding="utf-8")
        exported += 1

    _write_index(output_dir, all_entities)
    return exported


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


def _format_sheet_markdown(entity_type: str, raw_sheet: dict, raw_effects: list) -> list[str]:
    base_sheet = shm.normalize_sheet(raw_sheet)
    active_effects = fx.normalize_effects(raw_effects)
    sheet_data = fx.apply_to_sheet(base_sheet, active_effects)
    pb = shm.proficiency_bonus(entity_type, sheet_data)

    lines = ["## Character Sheet", ""]
    ability_parts = [
        f"{a.upper()} {sheet_data['abilities'][a]} ({shm.format_modifier(shm.ability_modifier(sheet_data['abilities'][a]))})"
        for a in shm.ABILITIES
    ]
    lines.append(f"- **Abilities:** {', '.join(ability_parts)}")
    lines.append(
        f"- **AC:** {sheet_data['ac']}  **HP:** {sheet_data['hp_current']}/{sheet_data['hp_max']}  "
        f"**Speed:** {sheet_data['speed']} ft.  **Proficiency Bonus:** {shm.format_modifier(pb)}"
    )
    if entity_type == "enemy":
        lines.append(f"- **CR:** {sheet_data['cr']}  **Creature Type:** {sheet_data['creature_type']}")
    else:
        lines.append(f"- **Level:** {sheet_data['level']}")

    if sheet_data["saving_throw_proficiencies"]:
        saves = ", ".join(
            f"{a.upper()} {shm.format_modifier(shm.saving_throw_bonus(sheet_data, a, pb))}"
            for a in shm.ABILITIES if a in sheet_data["saving_throw_proficiencies"]
        )
        lines.append(f"- **Saves:** {saves}")

    proficient_skills = [s for s in shm.SKILLS if sheet_data["skill_proficiencies"].get(s, "none") != "none"]
    if proficient_skills:
        skills_str = ", ".join(
            f"{shm.SKILL_LABELS[s]} {shm.format_modifier(shm.skill_bonus(sheet_data, s, pb))}"
            for s in proficient_skills
        )
        lines.append(f"- **Skills:** {skills_str}")

    if sheet_data["attacks"]:
        lines.append("- **Attacks:**")
        for atk in sheet_data["attacks"]:
            bonus = shm.format_modifier(int(atk.get("bonus", 0) or 0))
            lines.append(f"  - {atk.get('name', '?')} {bonus} to hit, {atk.get('damage', '')} {atk.get('damage_type', '')}".rstrip())

    for label, key in (("Resistances", "resistances"), ("Immunities", "immunities"), ("Vulnerabilities", "vulnerabilities")):
        if sheet_data[key]:
            lines.append(f"- **{label}:** {sheet_data[key]}")

    if sheet_data["special_abilities"]:
        lines.append("- **Special Abilities:**")
        for sa in sheet_data["special_abilities"]:
            lines.append(f"  - **{sa.get('name', '?')}:** {sa.get('description', '')}")

    for label, key in (("Senses", "senses"), ("Languages", "languages")):
        if sheet_data[key]:
            lines.append(f"- **{label}:** {sheet_data[key]}")

    if active_effects:
        lines.append("- **Active Effects:**")
        for effect in active_effects:
            duration = f"{effect['rounds_remaining']} rounds left" if effect["rounds_remaining"] is not None else "indefinite"
            lines.append(f"  - {effect['source']}: {shm.format_modifier(effect['modifier'])} {fx.STAT_LABELS[effect['stat']]} ({duration})")

    lines.append("")
    return lines


def _render_entity(entity: dict, include_stats: bool = True) -> str:
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
    if include_stats:
        if entity["type"] in shm.SHEET_ENTITY_TYPES and fields.get("sheet"):
            frontmatter["sheet"] = fields["sheet"]
        if entity["type"] in shm.SHEET_ENTITY_TYPES and fields.get("active_effects"):
            frontmatter["active_effects"] = fields["active_effects"]
        if entity["type"] == "encounter" and fields.get("combat"):
            frontmatter["combat"] = fields["combat"]
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

    # Character sheet (adventurer/enemy only, opt-in via include_stats)
    if include_stats and entity["type"] in shm.SHEET_ENTITY_TYPES:
        lines.extend(_format_sheet_markdown(entity["type"], fields.get("sheet", {}), fields.get("active_effects", [])))

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


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
_SECTION_RE_CACHE: dict[str, re.Pattern] = {}
_REL_LINE_RE = re.compile(r"^-\s*(?P<direction>.+?):\s*\[\[(?P<target>.+?)\]\](?:\s*—\s*(?P<notes>.*))?$")


def _section_pattern(heading: str) -> re.Pattern:
    if heading not in _SECTION_RE_CACHE:
        _SECTION_RE_CACHE[heading] = re.compile(rf"^## {re.escape(heading)}\n(.*?)(?=\n## |\Z)", re.DOTALL | re.MULTILINE)
    return _SECTION_RE_CACHE[heading]


def _extract_section(body: str, heading: str) -> str:
    match = _section_pattern(heading).search(body)
    return match.group(1).strip() if match else ""


def _unescape_wikilink(target: str) -> str:
    return target.replace("\\]", "]").replace("\\|", "|")


def _parse_vault_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(f"{path}: missing YAML frontmatter")

    frontmatter = yaml.safe_load(match.group(1)) or {}
    body = match.group(2)

    entity_type = frontmatter.get("type")
    name = frontmatter.get("name")
    if not entity_type or not name:
        raise ValueError(f"{path}: frontmatter missing 'type' or 'name'")
    if entity_type not in ENTITY_TYPES:
        raise ValueError(f"{path}: unknown entity type '{entity_type}'")

    fields = {k: v for k, v in frontmatter.items() if k not in _NON_SCHEMA_KEYS}
    for key in ("sheet", "active_effects", "combat"):
        if key in frontmatter:
            fields[key] = frontmatter[key]

    relationships = []
    for line in _extract_section(body, "Relationships").splitlines():
        rel_match = _REL_LINE_RE.match(line.strip())
        if not rel_match:
            continue
        direction = rel_match.group("direction").strip()
        if direction.startswith("←"):
            continue  # mirror of the forward relationship owned by the other entity's file
        target = _unescape_wikilink(rel_match.group("target"))
        notes = (rel_match.group("notes") or "").strip().replace("<br>", "\n")
        relationships.append((direction, target, notes))

    return {
        "type": str(entity_type),
        "name": str(name),
        "fields": fields,
        "notes": _extract_section(body, "Notes"),
        "created": frontmatter.get("created"),
        "updated": frontmatter.get("updated"),
        "relationships": relationships,
    }


def import_vault(input_dir: Path, *, replace: bool = False) -> dict[str, int]:
    """Import a vault produced by export_vault. Not intended for arbitrary
    hand-authored Obsidian vaults -- frontmatter must carry the same
    type/name/field shape this app writes."""
    input_dir = Path(input_dir).expanduser()
    if not input_dir.is_dir():
        raise ValueError(f"Not a directory: {input_dir}")

    md_files = sorted(p for p in input_dir.rglob("*.md") if p.name != "Index.md")
    if not md_files:
        raise ValueError("No entity files found in vault")

    parsed = [_parse_vault_file(p) for p in md_files]

    if not replace and (list_entities() or db.list_relationships()):
        raise ValueError("Refusing to import into a non-empty database without replace=True")

    now = datetime.now().isoformat(timespec="seconds")
    name_to_id: dict[str, int] = {}
    entities_to_insert = []
    for index, item in enumerate(parsed, start=1):
        created_at = f"{item['created']}T00:00:00" if item.get("created") else now
        updated_at = f"{item['updated']}T00:00:00" if item.get("updated") else now
        entities_to_insert.append({
            "id": index,
            "type": item["type"],
            "name": item["name"],
            "fields": item["fields"],
            "notes": item["notes"],
            "created_at": created_at,
            "updated_at": updated_at,
        })
        name_to_id[item["name"]] = index

    relationships_to_insert = []
    next_rel_id = 1
    for item in parsed:
        from_id = name_to_id[item["name"]]
        for rel_type, target_name, notes in item["relationships"]:
            to_id = name_to_id.get(target_name)
            if to_id is None:
                continue
            relationships_to_insert.append({
                "id": next_rel_id,
                "from_id": from_id,
                "to_id": to_id,
                "rel_type": rel_type,
                "notes": notes,
                "created_at": now,
            })
            next_rel_id += 1

    db.replace_all(entities_to_insert, relationships_to_insert)
    return {"entities": len(entities_to_insert), "relationships": len(relationships_to_insert)}
