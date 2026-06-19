"""Active effects: timed stat modifiers (potions, buffs, magic items)
layered on top of a character's base sheet (see sheet.py).

Effects live in an entity's fields["active_effects"] list. They are never
baked into the base sheet — apply_to_sheet() computes an effective sheet on
read. Effects only decay once per combat round (ticked from
CombatTrackerScreen via tick_effects()); nothing decays outside of combat,
matching the round-scoped time system decided for this project.
"""
import sheet as shm

MODIFIABLE_STATS = [*shm.ABILITIES, "ac", "speed"]

STAT_LABELS = {**shm.ABILITY_LABELS, "ac": "Armor Class", "speed": "Speed"}


def normalize_effects(raw: list | None) -> list[dict]:
    effects = []
    for item in raw or []:
        stat = item.get("stat")
        if stat not in MODIFIABLE_STATS:
            continue
        try:
            modifier = int(item.get("modifier", 0) or 0)
        except (TypeError, ValueError):
            modifier = 0
        rounds_remaining = item.get("rounds_remaining")
        if rounds_remaining is not None:
            try:
                rounds_remaining = int(rounds_remaining)
            except (TypeError, ValueError):
                rounds_remaining = None
        effects.append({
            "source": str(item.get("source", "")),
            "stat": stat,
            "modifier": modifier,
            "rounds_remaining": rounds_remaining,
        })
    return effects


def add_effect(effects: list[dict], source: str, stat: str, modifier: int, rounds_remaining: int | None) -> list[dict]:
    effects = normalize_effects(effects)
    effects.append({"source": source, "stat": stat, "modifier": modifier, "rounds_remaining": rounds_remaining})
    return effects


def remove_effect(effects: list[dict], index: int) -> list[dict]:
    effects = normalize_effects(effects)
    if 0 <= index < len(effects):
        effects.pop(index)
    return effects


def tick_effects(effects: list[dict]) -> tuple[list[dict], list[dict]]:
    """Decrement rounds_remaining by one round. Returns (kept, expired)."""
    kept, expired = [], []
    for effect in normalize_effects(effects):
        if effect["rounds_remaining"] is None:
            kept.append(effect)
            continue
        effect["rounds_remaining"] -= 1
        if effect["rounds_remaining"] > 0:
            kept.append(effect)
        else:
            expired.append(effect)
    return kept, expired


def apply_to_sheet(sheet: dict, effects: list[dict]) -> dict:
    """Return a new sheet with all active effect modifiers applied.
    Never mutates the base sheet, the effects list, or any individual effect."""
    effective = dict(sheet)
    effective["abilities"] = dict(sheet["abilities"])
    for effect in normalize_effects(effects):
        stat = effect["stat"]
        if stat in effective["abilities"]:
            effective["abilities"][stat] += effect["modifier"]
        else:
            effective[stat] = effective[stat] + effect["modifier"]
    return effective
