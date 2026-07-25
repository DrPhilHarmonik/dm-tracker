"""Roll20 character JSON importer.

Targets the Roll20 "D&D 5th Edition by Roll20" sheet export format
(schema_version 3). Roll20 has no first-party export UI; this format is
produced by community API scripts (e.g. the "Export Sheet" script or
one-click exporters available in the Roll20 marketplace).

The export is either a bare character object or a {"characters": [...]} wrapper.
Attributes are stored as a flat list of {name, current, max} objects.

Reliably mapped:  name, ability scores, HP, AC, speed, level.
Best-effort:      skill proficiencies (_prof suffix convention), race, class.
Skipped:          spells, equipment, repeating rows -- sheet-template-specific.
"""
import json
from pathlib import Path

import sheet as shm

_ABILITY_ATTRS = {
    "strength": "str", "dexterity": "dex", "constitution": "con",
    "intelligence": "int", "wisdom": "wis", "charisma": "cha",
}

_SKILL_PROF_ATTRS = {
    "acrobatics_prof": "acrobatics",
    "animal_handling_prof": "animal_handling",
    "arcana_prof": "arcana",
    "athletics_prof": "athletics",
    "deception_prof": "deception",
    "history_prof": "history",
    "insight_prof": "insight",
    "intimidation_prof": "intimidation",
    "investigation_prof": "investigation",
    "medicine_prof": "medicine",
    "nature_prof": "nature",
    "perception_prof": "perception",
    "performance_prof": "performance",
    "persuasion_prof": "persuasion",
    "religion_prof": "religion",
    "sleight_of_hand_prof": "sleight_of_hand",
    "stealth_prof": "stealth",
    "survival_prof": "survival",
}


def parse_roll20_json(path: str | Path) -> dict:
    """Parse a Roll20 character sheet JSON export.

    Returns the standard importer intermediate shape:
        {"name", "entity_type", "fields", "notes"}

    Raises ValueError with a human-readable message on format mismatch.
    """
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"Could not read JSON: {e}") from e

    # Accept {"characters": [...]} wrapper from bulk exports
    if isinstance(raw, dict) and "characters" in raw:
        chars = raw.get("characters") or []
        if not chars:
            raise ValueError("No characters found in Roll20 export file.")
        raw = chars[0]

    if "attribs" not in raw:
        raise ValueError(
            "File does not look like a Roll20 character export (missing 'attribs'). "
            "Export via the Roll20 API or a community export script."
        )

    name = str(raw.get("name") or "Imported Character").strip() or "Imported Character"

    # Build attribute lookup (case-insensitive, first occurrence wins)
    attrs: dict[str, str] = {}
    for attr in raw.get("attribs") or []:
        attr_name = str(attr.get("name") or "").lower().strip()
        current = attr.get("current")
        if attr_name and attr_name not in attrs and current is not None:
            attrs[attr_name] = str(current).strip()

    def _int(key: str, default: int) -> int:
        try:
            return int(attrs.get(key, default))
        except (TypeError, ValueError):
            return default

    # -- Abilities --
    abilities = {ability: _int(attr_name, 10) for attr_name, ability in _ABILITY_ATTRS.items()}

    # -- Combat stats --
    hp_max = _int("hp_max", 10)
    hp_current = _int("hp", hp_max)
    ac = _int("ac", 10)
    speed = _int("speed", 30)
    level = max(1, _int("level", 1))

    # -- Skill proficiencies (1 = proficient, 2 = expertise) --
    skill_profs: dict[str, str] = {}
    for attr_name, skill_name in _SKILL_PROF_ATTRS.items():
        try:
            val = int(attrs.get(attr_name, 0))
        except (TypeError, ValueError):
            val = 0
        if val >= 1:
            skill_profs[skill_name] = "expertise" if val >= 2 else "proficient"

    race = str(attrs.get("race") or "").strip()
    class_name = str(attrs.get("class") or "").strip()
    notes = str(raw.get("bio") or attrs.get("background") or "").strip()

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
            "speed": speed,
            "skill_proficiencies": skill_profs,
        }),
    }

    return {"name": name, "entity_type": "adventurer", "fields": fields, "notes": notes}
