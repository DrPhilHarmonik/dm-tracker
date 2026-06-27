"""CSV entity importer.

Expected columns:  name, type, notes  (always required)
Flat fields:       any column matching the entity's ENTITY_SCHEMAS key
Sheet columns:     str, dex, con, int, wis, cha, ac, hp_max, speed, level (adventurer)
                   cr, creature_type (enemy)

Column names are case-insensitive. Unknown columns are silently ignored.
Each row is independent; type must be a known entity type.

CSV template layout (example):

    name,type,race,class_name,level,str,dex,con,int,wis,cha,ac,hp_max,speed,notes
    Brynn Ashforge,adventurer,Human,Fighter,5,15,14,13,12,10,8,16,40,30,Veteran soldier
    name,type,cr,creature_type,ac,hp_max,str,dex,con,int,wis,cha,notes
    Goblin Boss,enemy,1,Humanoid,15,21,10,14,12,8,8,10,Cunning leader
"""
import csv
import io
from pathlib import Path

import sheet as shm
from models import ENTITY_SCHEMAS, ENTITY_TYPES

_ABILITY_COLS = set(shm.ABILITIES)
_ADVENTURER_SHEET_COLS = {"ac", "hp_max", "speed", "level", "hit_dice",
                          "proficiencies", "spellcasting_ability"}
_ENEMY_SHEET_COLS = {"ac", "hp_max", "speed", "cr", "creature_type"}
_RESERVED = {"name", "type", "notes"}


def _try_int(val: str, default) -> int | str:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def parse_csv(path: str | Path) -> list[dict]:
    """Parse a CSV file and return a list of importer intermediate dicts.

    Rows with missing/unknown type or empty name are skipped with no error.
    """
    text = Path(path).read_text(encoding="utf-8-sig")  # handle Excel BOM
    reader = csv.DictReader(io.StringIO(text))
    results = []
    for row in reader:
        # Normalize column names
        row = {k.strip().lower(): v.strip() for k, v in row.items() if k}
        name = row.get("name", "").strip()
        entity_type = row.get("type", "").strip().lower()
        notes = row.get("notes", "").strip()

        if not name or entity_type not in ENTITY_TYPES:
            continue

        schema = ENTITY_SCHEMAS.get(entity_type, [])
        flat_keys = {s[0] for s in schema if s[2] not in ("entity_ref",)}

        fields: dict = {}
        abilities: dict[str, int] = {}
        sheet_update: dict = {}

        for col, raw_val in row.items():
            if col in _RESERVED or not raw_val:
                continue
            if col in _ABILITY_COLS:
                abilities[col] = _try_int(raw_val, 10)
            elif entity_type == "adventurer" and col in _ADVENTURER_SHEET_COLS:
                sheet_update[col] = _try_int(raw_val, raw_val)
            elif entity_type == "enemy" and col in _ENEMY_SHEET_COLS:
                sheet_update[col] = _try_int(raw_val, raw_val)
            elif col in flat_keys:
                fields[col] = raw_val

        # Assemble sheet for sheet-bearing entity types
        if entity_type in ("adventurer", "enemy"):
            if abilities:
                sheet_update["abilities"] = abilities
            fields["sheet"] = shm.normalize_sheet(sheet_update)
            sheet = fields["sheet"]
            # Sync denormalized flat copies
            if entity_type == "adventurer":
                fields["level"] = int(sheet.get("level") or 1)
            elif entity_type == "enemy":
                fields["cr"] = str(sheet.get("cr") or "0")
                fields["creature_type"] = str(sheet.get("creature_type") or "")

        results.append({
            "name": name,
            "entity_type": entity_type,
            "fields": fields,
            "notes": notes,
        })
    return results


CSV_TEMPLATE = """\
name,type,race,class_name,level,cr,creature_type,role,alignment,status,str,dex,con,int,wis,cha,ac,hp_max,speed,notes
Brynn Ashforge,adventurer,Human,Fighter,5,,,,Lawful Good,Active,15,14,13,12,10,8,16,44,30,Veteran soldier
Lyra Moonwhisper,adventurer,High Elf,Wizard,3,,,,Neutral Good,Active,8,14,13,16,10,12,12,20,30,Elven scholar
Goblin Boss,enemy,,,, 1,Humanoid,,Neutral Evil,Alive,10,14,10,10,8,8,15,21,30,Cunning and cowardly
Ogre,enemy,,,,2,Giant,,Chaotic Evil,Alive,19,8,16,5,7,7,11,59,30,Big and slow
Mira the Innkeeper,npc,Human,,,,,Innkeeper,Neutral Good,Alive,,,,,,,,,,Runs the Laughing Flagon
Saltmarsh,location,,,,,,,,,,,,,,,,,,Fishing town on the coast
"""


def write_template(path: str | Path) -> None:
    """Write a CSV template with example rows for each common entity type."""
    Path(path).write_text(CSV_TEMPLATE, encoding="utf-8")
