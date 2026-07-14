"""Short-rest hit-die spending and long-rest full recovery."""
import re

import classes
import dice as dce
import sheet as shm


def _hit_die_sides(sheet: dict) -> int:
    """Derive hit die sides from class_name, falling back to the hit_dice field."""
    class_name = sheet.get("class_name") or ""
    if class_name in classes.CLASS_HIT_DICE:
        return classes.CLASS_HIT_DICE[class_name]
    # Parse from stored notation like "5d8+10"
    m = re.search(r"d(\d+)", str(sheet.get("hit_dice") or ""))
    return int(m.group(1)) if m else 8


def roll_hit_dice(sheet: dict, count: int) -> tuple[int, str]:
    """Roll `count` hit dice + CON mod each. Returns (total_hp_gain, detail_str)."""
    if count <= 0:
        return 0, "0"
    sides = _hit_die_sides(sheet)
    con_mod = shm.ability_modifier(sheet["abilities"].get("con", 10))
    totals = []
    details = []
    for _ in range(count):
        result = dce.roll(f"1d{sides}")
        gain = max(1, result.total + con_mod)
        totals.append(gain)
        mod_str = shm.format_modifier(con_mod) if con_mod != 0 else ""
        details.append(f"{result.total}{mod_str}={gain}")
    total = sum(totals)
    return total, f"{count}d{sides}: {', '.join(details)} = {total}"


def apply_short_rest(sheet: dict, hp_gain: int) -> dict:
    """Add hp_gain to current HP, clamped to hp_max. Returns updated sheet copy."""
    sheet = dict(sheet)
    sheet["hp_current"] = min(sheet["hp_max"], sheet["hp_current"] + hp_gain)
    return sheet


def apply_long_rest(sheet: dict) -> dict:
    """Full HP restore, all spell slots restored to max. Returns updated sheet copy."""
    sheet = dict(sheet)
    sheet["hp_current"] = sheet["hp_max"]
    sheet["spell_slots"] = {
        lvl: {"current": slot["max"], "max": slot["max"]}
        for lvl, slot in sheet.get("spell_slots", {}).items()
    }
    return sheet


def active_adventurers() -> list[dict]:
    """Return all adventurer entities with status != Dead/Retired."""
    import db
    result = []
    for e in db.list_entities("adventurer"):
        status = e["fields"].get("status", "Active")
        if status not in ("Dead", "Retired"):
            result.append(e)
    return result
