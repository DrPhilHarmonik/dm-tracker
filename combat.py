"""Encounter/combat state management.

Combat state lives in an Encounter entity's ``fields["combat"]`` as a plain
dict. Every function here is a pure transformation — callers persist the
returned dict via ``db.update_entity``. HP itself is never stored here; it
lives on the combatant's own character sheet (see sheet.py) so there is one
source of truth.
"""


def default_combat() -> dict:
    return {"round": 1, "turn_index": 0, "started": False, "combatants": []}


def normalize_combat(raw: dict | None) -> dict:
    combat = default_combat()
    raw = raw or {}
    combat["round"] = int(raw.get("round") or 1)
    combat["turn_index"] = int(raw.get("turn_index") or 0)
    combat["started"] = bool(raw.get("started", False))
    combat["combatants"] = [
        {
            "entity_id": int(c["entity_id"]),
            "initiative": int(c.get("initiative") or 0),
            "conditions": [
                {"name": str(cond.get("name", "")), "rounds_remaining": cond.get("rounds_remaining")}
                for cond in (c.get("conditions") or [])
            ],
            "death_saves": {
                "successes": max(0, min(3, int((c.get("death_saves") or {}).get("successes") or 0))),
                "failures": max(0, min(3, int((c.get("death_saves") or {}).get("failures") or 0))),
            },
        }
        for c in (raw.get("combatants") or [])
    ]
    return combat


def add_combatant(combat: dict, entity_id: int) -> dict:
    combat = normalize_combat(combat)
    if any(c["entity_id"] == entity_id for c in combat["combatants"]):
        return combat
    combat["combatants"].append({
        "entity_id": entity_id,
        "initiative": 0,
        "conditions": [],
        "death_saves": {"successes": 0, "failures": 0},
    })
    return combat


def remove_combatant(combat: dict, entity_id: int) -> dict:
    combat = normalize_combat(combat)
    idx = next((i for i, c in enumerate(combat["combatants"]) if c["entity_id"] == entity_id), None)
    if idx is None:
        return combat
    combat["combatants"].pop(idx)
    if combat["combatants"]:
        combat["turn_index"] %= len(combat["combatants"])
    else:
        combat["turn_index"] = 0
        combat["started"] = False
    return combat


def set_initiative(combat: dict, entity_id: int, initiative: int) -> dict:
    combat = normalize_combat(combat)
    for c in combat["combatants"]:
        if c["entity_id"] == entity_id:
            c["initiative"] = initiative
    return combat


def start_encounter(combat: dict) -> dict:
    combat = normalize_combat(combat)
    combat["combatants"].sort(key=lambda c: c["initiative"], reverse=True)
    combat["started"] = True
    combat["round"] = 1
    combat["turn_index"] = 0
    return combat


def current_combatant(combat: dict) -> dict | None:
    combat = normalize_combat(combat)
    if not combat["combatants"]:
        return None
    return combat["combatants"][combat["turn_index"] % len(combat["combatants"])]


def next_turn(combat: dict) -> dict:
    combat = normalize_combat(combat)
    if not combat["combatants"]:
        return combat
    combat["turn_index"] += 1
    if combat["turn_index"] >= len(combat["combatants"]):
        combat["turn_index"] = 0
        combat["round"] += 1
        _tick_conditions(combat)
    return combat


def next_round(combat: dict) -> dict:
    combat = normalize_combat(combat)
    combat["turn_index"] = 0
    combat["round"] += 1
    _tick_conditions(combat)
    return combat


def _tick_conditions(combat: dict):
    for c in combat["combatants"]:
        kept = []
        for cond in c["conditions"]:
            if cond["rounds_remaining"] is None:
                kept.append(cond)
                continue
            cond["rounds_remaining"] -= 1
            if cond["rounds_remaining"] > 0:
                kept.append(cond)
        c["conditions"] = kept


def add_condition(combat: dict, entity_id: int, name: str, rounds_remaining: int | None) -> dict:
    combat = normalize_combat(combat)
    for c in combat["combatants"]:
        if c["entity_id"] == entity_id:
            c["conditions"].append({"name": name, "rounds_remaining": rounds_remaining})
    return combat


def remove_condition(combat: dict, entity_id: int, index: int) -> dict:
    combat = normalize_combat(combat)
    for c in combat["combatants"]:
        if c["entity_id"] == entity_id and 0 <= index < len(c["conditions"]):
            c["conditions"].pop(index)
    return combat


def add_death_save(combat: dict, entity_id: int, success: bool) -> tuple[dict, str | None]:
    """Record one death save result. Returns (combat, resolution) where
    resolution is 'stable' (3 successes), 'dead' (3 failures), or None."""
    combat = normalize_combat(combat)
    for c in combat["combatants"]:
        if c["entity_id"] == entity_id:
            if success:
                c["death_saves"]["successes"] = min(3, c["death_saves"]["successes"] + 1)
                if c["death_saves"]["successes"] >= 3:
                    return combat, "stable"
            else:
                c["death_saves"]["failures"] = min(3, c["death_saves"]["failures"] + 1)
                if c["death_saves"]["failures"] >= 3:
                    return combat, "dead"
            return combat, None
    return combat, None


def reset_death_saves(combat: dict, entity_id: int) -> dict:
    combat = normalize_combat(combat)
    for c in combat["combatants"]:
        if c["entity_id"] == entity_id:
            c["death_saves"] = {"successes": 0, "failures": 0}
    return combat


def apply_damage(hp_current: int, amount: int) -> int:
    return max(0, hp_current - amount)


def apply_heal(hp_current: int, hp_max: int, amount: int) -> int:
    return min(hp_max, hp_current + amount)
