"""Foundry VTT actor JSON importer.

Targets Foundry VTT 10+ actor JSON (exported via Actors sidebar >
right-click > Export Data). Handles both "character" (PC) and "npc" actor
types -- PCs become adventurers, NPCs become enemies.

Reliably mapped:  name, ability scores, HP, AC, walk speed, skills (prof/exp).
Best-effort:      level (characters), CR (NPCs), race, class, biography.
Skipped:          items, spells, feats -- too schema-specific across systems.
"""
import json
import re
from pathlib import Path

import sheet as shm

_ABILITY_KEYS = {"str", "dex", "con", "int", "wis", "cha"}

_SKILL_MAP = {
    "acr": "acrobatics", "ani": "animal_handling", "arc": "arcana",
    "ath": "athletics", "dec": "deception", "his": "history",
    "ins": "insight", "itm": "intimidation", "inv": "investigation",
    "med": "medicine", "nat": "nature", "prc": "perception",
    "prf": "performance", "per": "persuasion", "rel": "religion",
    "slt": "sleight_of_hand", "ste": "stealth", "sur": "survival",
}

_CR_FRACTIONS = {0.125: "1/8", 0.25: "1/4", 0.5: "1/2"}


def parse_foundry_json(path: str | Path) -> dict:
    """Parse a Foundry VTT actor JSON export.

    Returns the standard importer intermediate shape:
        {"name", "entity_type", "fields", "notes"}

    Raises ValueError with a human-readable message on format mismatch.
    """
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"Could not read JSON: {e}") from e

    if "name" not in raw or "system" not in raw:
        raise ValueError(
            "File does not look like a Foundry VTT actor export "
            "(missing 'name' or 'system'). "
            "Export via Actors sidebar > right-click > Export Data."
        )

    actor_type = str(raw.get("type") or "character")
    sys = raw.get("system") or {}
    name = str(raw.get("name") or "Imported Actor").strip() or "Imported Actor"

    # -- Abilities --
    abilities = {a: 10 for a in shm.ABILITIES}
    for key, val_dict in (sys.get("abilities") or {}).items():
        if key in _ABILITY_KEYS and isinstance(val_dict, dict):
            try:
                abilities[key] = int(val_dict.get("value") or 10)
            except (TypeError, ValueError):
                pass

    # -- HP, AC, speed --
    attrs = sys.get("attributes") or {}
    hp_block = attrs.get("hp") or {}
    hp_max = _to_int(hp_block.get("max") or hp_block.get("value"), 10)
    hp_current = _to_int(hp_block.get("value"), hp_max)
    ac_block = attrs.get("ac") or {}
    ac = _to_int(ac_block.get("value") or ac_block.get("flat"), 10)
    movement = attrs.get("movement") or {}
    speed = _to_int(movement.get("walk"), 30)

    # -- Details --
    details = sys.get("details") or {}
    level_raw = details.get("level")
    level = _to_int(level_raw.get("value") if isinstance(level_raw, dict) else level_raw, 1)
    level = max(1, level)
    cr_raw = details.get("cr")
    race = str(details.get("race") or "").strip()
    class_name = str(details.get("class") or "").strip()

    # -- Biography (strip HTML) --
    bio_raw = details.get("biography") or {}
    bio_text = str(bio_raw.get("value") if isinstance(bio_raw, dict) else bio_raw or "")
    notes = re.sub(r"<[^>]+>", "", bio_text).strip()

    # -- Skill proficiencies (characters only) --
    skill_profs: dict[str, str] = {}
    for abbr, skill_name in _SKILL_MAP.items():
        sk = (sys.get("skills") or {}).get(abbr) or {}
        prof_val = _to_int(sk.get("value"), 0)
        if prof_val >= 1:
            skill_profs[skill_name] = "expertise" if prof_val >= 2 else "proficient"

    if actor_type == "npc":
        try:
            cr_float = float(cr_raw)
            cr_str = _CR_FRACTIONS.get(cr_float) or (
                str(int(cr_float)) if cr_float == int(cr_float) else str(cr_float)
            )
        except (TypeError, ValueError):
            cr_str = "0"
        fields = {
            "cr": cr_str,
            "creature_type": race,
            "sheet": shm.normalize_sheet({
                "abilities": abilities,
                "ac": ac,
                "hp_max": hp_max,
                "hp_current": hp_current,
                "cr": cr_str,
                "creature_type": race,
            }),
        }
        return {"name": name, "entity_type": "enemy", "fields": fields, "notes": notes}

    fields = {
        "race": race,
        "class_name": class_name,
        "level": level,
        "sheet": shm.normalize_sheet({
            "abilities": abilities,
            "ac": ac,
            "hp_max": hp_max,
            "hp_current": hp_current,
            "level": level,
            "skill_proficiencies": skill_profs,
        }),
    }
    return {"name": name, "entity_type": "adventurer", "fields": fields, "notes": notes}


def _to_int(val, default: int) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default
