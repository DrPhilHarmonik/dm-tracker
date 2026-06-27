"""D&D Beyond character JSON export importer.

Targets the current (2023+) D&D Beyond export format. Older exports may wrap
everything under a top-level "data" key -- we detect and unwrap that.

Reliably mapped:  name, ability scores, class/level, HP, AC, speed, race, notes.
Best-effort:      skill proficiencies (via skills[].value: 1=prof, 2=expertise),
                  saving throw proficiencies (via the classes saving-throw list).
Skipped:          spell slots, equipment, feats, actions -- out of scope for import.
"""
import json
from pathlib import Path

import sheet as shm
import classes as cls_mod

_STAT_IDS: dict[int, str] = {1: "str", 2: "dex", 3: "con", 4: "int", 5: "wis", 6: "cha"}

_SKILL_IDS: dict[int, str] = {
    1: "acrobatics", 2: "animal_handling", 3: "arcana", 4: "athletics",
    5: "deception", 6: "history", 7: "insight", 8: "intimidation",
    9: "investigation", 10: "medicine", 11: "nature", 12: "perception",
    13: "performance", 14: "persuasion", 15: "religion",
    16: "sleight_of_hand", 17: "stealth", 18: "survival",
}


def _unwrap(data: dict) -> dict:
    """Strip the 'data' wrapper some DDB export endpoints add."""
    if "data" in data and isinstance(data["data"], dict) and "name" in data["data"]:
        return data["data"]
    return data


def parse_ddb_json(path: str | Path) -> dict:
    """Parse a D&D Beyond character export JSON.

    Returns the standard importer intermediate shape:
        {"name", "entity_type", "fields", "notes"}

    Raises ValueError with a human-readable message if the file doesn't look
    like a DDB character export.
    """
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"Could not read JSON: {e}") from e

    char = _unwrap(raw)

    if "name" not in char or "stats" not in char:
        raise ValueError(
            "File does not look like a D&D Beyond character export "
            "(missing 'name' or 'stats' keys). "
            "Export your character from the D&D Beyond character sheet page."
        )

    name = str(char.get("name", "Imported Character")).strip() or "Imported Character"

    # -- Ability scores --
    abilities = {a: 10 for a in shm.ABILITIES}
    for stat in char.get("stats") or []:
        key = _STAT_IDS.get(int(stat.get("id") or 0))
        val = stat.get("value")
        if key and val is not None:
            try:
                abilities[key] = int(val)
            except (TypeError, ValueError):
                pass

    # -- Classes / level --
    classes_list = char.get("classes") or []
    primary_class = ""
    total_level = 0
    for cls in classes_list:
        lvl = int(cls.get("level") or 0)
        total_level += lvl
        defn = cls.get("definition") or {}
        if cls.get("isStartingClass") or not primary_class:
            primary_class = str(defn.get("name") or "")

    total_level = max(1, total_level)

    # -- HP --
    base_hp = int(char.get("baseHitPoints") or 0) + int(char.get("bonusHitPoints") or 0)
    override_hp = char.get("overrideHitPoints")
    if override_hp is not None:
        try:
            base_hp = int(override_hp)
        except (TypeError, ValueError):
            pass
    base_hp = max(1, base_hp)
    removed_hp = max(0, int(char.get("removedHitPoints") or 0))
    temp_hp = max(0, int(char.get("temporaryHitPoints") or 0))
    hp_current = max(0, base_hp - removed_hp)

    # -- AC --
    ac = int(char.get("armorClass") or 10)

    # -- Speed --
    speed = 30
    race_obj = char.get("race") or {}
    try:
        walk = (race_obj.get("weightSpeeds") or {}).get("normal", {}).get("walk")
        if walk:
            speed = int(walk)
    except (TypeError, ValueError, AttributeError):
        pass

    # -- Race --
    race_name = str(race_obj.get("fullName") or race_obj.get("baseRaceName") or "").strip()

    # -- Skill proficiencies (best-effort) --
    skill_profs: dict[str, str] = {}
    for sk in char.get("skills") or []:
        skill_id = int(sk.get("id") or 0)
        prof_value = int(sk.get("value") or 0)
        skill_name = _SKILL_IDS.get(skill_id)
        if skill_name and prof_value >= 1:
            skill_profs[skill_name] = "expertise" if prof_value >= 2 else "proficient"

    # -- Saving throw proficiencies (from class definition if present) --
    saving_throw_profs: list[str] = list(cls_mod.CLASS_SAVING_THROWS.get(primary_class, []))

    # -- Notes from backstory + traits --
    notes_parts: list[str] = []
    notes_obj = char.get("notes") or {}
    traits_obj = char.get("traits") or {}
    for key, label in [
        ("backstory", "Backstory"),
        ("allies", "Allies & Organizations"),
        ("enemies", "Enemies"),
        ("other", "Other Notes"),
    ]:
        val = str(notes_obj.get(key) or "").strip()
        if val:
            notes_parts.append(f"**{label}**\n{val}")
    for key, label in [
        ("personalityTraits", "Personality Traits"),
        ("ideals", "Ideals"),
        ("bonds", "Bonds"),
        ("flaws", "Flaws"),
    ]:
        val = str(traits_obj.get(key) or "").strip()
        if val:
            notes_parts.append(f"**{label}**: {val}")
    notes = "\n\n".join(notes_parts)

    # -- Build sheet --
    sheet = shm.normalize_sheet({
        "abilities": abilities,
        "ac": ac,
        "hp_max": base_hp,
        "hp_current": hp_current,
        "hp_temp": temp_hp,
        "speed": speed,
        "level": total_level,
        "skill_proficiencies": skill_profs,
        "saving_throw_proficiencies": saving_throw_profs,
        "hit_dice": cls_mod.hit_dice_notation(primary_class, total_level) if primary_class else "",
        "proficiencies": cls_mod.CLASS_PROFICIENCIES.get(primary_class, ""),
        "spellcasting_ability": cls_mod.CLASS_SPELLCASTING_ABILITY.get(primary_class) or "",
    })

    fields = {
        "sheet": sheet,
        "race": race_name,
        "class_name": primary_class,
        "level": total_level,
    }

    return {
        "name": name,
        "entity_type": "adventurer",
        "fields": fields,
        "notes": notes,
    }
