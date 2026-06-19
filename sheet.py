"""D&D 5e character sheet data shape and derived-stat math.

Sheets are stored as plain JSON inside an entity's ``fields["sheet"]``.
Nothing here mutates a sheet in place; callers read normalized copies and
write back whatever they changed.
"""
from fractions import Fraction

ABILITIES = ["str", "dex", "con", "int", "wis", "cha"]

ABILITY_LABELS = {
    "str": "Strength",
    "dex": "Dexterity",
    "con": "Constitution",
    "int": "Intelligence",
    "wis": "Wisdom",
    "cha": "Charisma",
}

SKILLS = {
    "acrobatics": "dex",
    "animal_handling": "wis",
    "arcana": "int",
    "athletics": "str",
    "deception": "cha",
    "history": "int",
    "insight": "wis",
    "intimidation": "cha",
    "investigation": "int",
    "medicine": "wis",
    "nature": "int",
    "perception": "wis",
    "performance": "cha",
    "persuasion": "cha",
    "religion": "int",
    "sleight_of_hand": "dex",
    "stealth": "dex",
    "survival": "wis",
}

SKILL_LABELS = {
    "acrobatics": "Acrobatics",
    "animal_handling": "Animal Handling",
    "arcana": "Arcana",
    "athletics": "Athletics",
    "deception": "Deception",
    "history": "History",
    "insight": "Insight",
    "intimidation": "Intimidation",
    "investigation": "Investigation",
    "medicine": "Medicine",
    "nature": "Nature",
    "perception": "Perception",
    "performance": "Performance",
    "persuasion": "Persuasion",
    "religion": "Religion",
    "sleight_of_hand": "Sleight of Hand",
    "stealth": "Stealth",
    "survival": "Survival",
}

STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]

# entity types that carry a full character sheet
SHEET_ENTITY_TYPES = ("adventurer", "enemy")


def default_sheet() -> dict:
    return {
        "abilities": {a: 10 for a in ABILITIES},
        "ac": 10,
        "hp_max": 10,
        "hp_current": 10,
        "hp_temp": 0,
        "hit_dice": "",
        "speed": 30,
        "level": 1,
        "cr": "0",
        "creature_type": "",
        "saving_throw_proficiencies": [],
        "skill_proficiencies": {},
        "senses": "",
        "languages": "",
        "attacks": [],
        "resistances": "",
        "immunities": "",
        "vulnerabilities": "",
        "special_abilities": [],
    }


def normalize_sheet(raw: dict | None) -> dict:
    """Fill in any missing keys so callers never hit a KeyError, including
    for sheets created before a field existed."""
    sheet = default_sheet()
    raw = raw or {}
    sheet.update({k: v for k, v in raw.items() if k in sheet})

    abilities = sheet["abilities"]
    abilities.update(raw.get("abilities") or {})
    sheet["abilities"] = {a: abilities.get(a, 10) for a in ABILITIES}

    sheet["saving_throw_proficiencies"] = list(raw.get("saving_throw_proficiencies") or [])
    sheet["skill_proficiencies"] = dict(raw.get("skill_proficiencies") or {})
    sheet["attacks"] = list(raw.get("attacks") or [])
    sheet["special_abilities"] = list(raw.get("special_abilities") or [])
    return sheet


def ability_modifier(score) -> int:
    try:
        score = int(score)
    except (TypeError, ValueError):
        score = 10
    return (score - 10) // 2


def format_modifier(value: int) -> str:
    return f"+{value}" if value >= 0 else str(value)


def parse_cr(cr) -> Fraction:
    try:
        return Fraction(str(cr).strip() or "0")
    except (ValueError, ZeroDivisionError):
        return Fraction(0)


def proficiency_bonus_for_level(level) -> int:
    try:
        level = int(level)
    except (TypeError, ValueError):
        level = 1
    if level < 5:
        return 2
    if level < 9:
        return 3
    if level < 13:
        return 4
    if level < 17:
        return 5
    return 6


def proficiency_bonus_for_cr(cr) -> int:
    value = parse_cr(cr)
    if value < 5:
        return 2
    if value < 9:
        return 3
    if value < 13:
        return 4
    if value < 17:
        return 5
    if value < 21:
        return 6
    if value < 25:
        return 7
    if value < 29:
        return 8
    return 9


def proficiency_bonus(entity_type: str, sheet: dict) -> int:
    if entity_type == "enemy":
        return proficiency_bonus_for_cr(sheet.get("cr", "0"))
    return proficiency_bonus_for_level(sheet.get("level", 1))


def saving_throw_bonus(sheet: dict, ability: str, prof_bonus: int) -> int:
    mod = ability_modifier(sheet["abilities"].get(ability, 10))
    proficient = ability in sheet.get("saving_throw_proficiencies", [])
    return mod + (prof_bonus if proficient else 0)


def skill_bonus(sheet: dict, skill: str, prof_bonus: int) -> int:
    ability = SKILLS[skill]
    mod = ability_modifier(sheet["abilities"].get(ability, 10))
    level = sheet.get("skill_proficiencies", {}).get(skill, "none")
    if level == "expertise":
        return mod + prof_bonus * 2
    if level == "proficient":
        return mod + prof_bonus
    return mod


def initiative_bonus(sheet: dict) -> int:
    return ability_modifier(sheet["abilities"].get("dex", 10))


def matches_standard_array(scores: dict) -> bool:
    return sorted(scores.values()) == sorted(STANDARD_ARRAY)


def suggested_ac(dex_modifier: int) -> int:
    return 10 + dex_modifier
