import effects
import sheet as shm


def test_normalize_effects_drops_invalid_stats_and_coerces_types():
    raw = [
        {"source": "Potion of Giant Strength", "stat": "str", "modifier": "4", "rounds_remaining": "10"},
        {"source": "Bogus", "stat": "luck", "modifier": 1, "rounds_remaining": None},
        {"source": "Indefinite Buff", "stat": "ac", "modifier": 2, "rounds_remaining": None},
    ]
    normalized = effects.normalize_effects(raw)
    assert len(normalized) == 2
    assert normalized[0] == {"source": "Potion of Giant Strength", "stat": "str", "modifier": 4, "rounds_remaining": 10}
    assert normalized[1]["rounds_remaining"] is None


def test_add_and_remove_effect():
    state = effects.add_effect([], "Bull's Strength", "str", 2, 10)
    state = effects.add_effect(state, "Ring of Protection", "ac", 1, None)
    assert len(state) == 2
    state = effects.remove_effect(state, 0)
    assert [e["source"] for e in state] == ["Ring of Protection"]


def test_tick_effects_decrements_and_expires():
    state = [
        {"source": "Haste", "stat": "speed", "modifier": 30, "rounds_remaining": 1},
        {"source": "Blessed", "stat": "dex", "modifier": 1, "rounds_remaining": None},
        {"source": "Bull's Strength", "stat": "str", "modifier": 4, "rounds_remaining": 3},
    ]
    kept, expired = effects.tick_effects(state)
    assert [e["source"] for e in expired] == ["Haste"]
    by_source = {e["source"]: e["rounds_remaining"] for e in kept}
    assert by_source == {"Blessed": None, "Bull's Strength": 2}


def test_tick_effects_does_not_mutate_input():
    state = [{"source": "Haste", "stat": "speed", "modifier": 30, "rounds_remaining": 1}]
    effects.tick_effects(state)
    assert state[0]["rounds_remaining"] == 1


def test_apply_to_sheet_adds_ability_modifiers():
    base = shm.normalize_sheet({"abilities": {"str": 14}})
    active = [{"source": "Potion of Giant Strength", "stat": "str", "modifier": 4, "rounds_remaining": 10}]
    effective = effects.apply_to_sheet(base, active)
    assert effective["abilities"]["str"] == 18
    assert base["abilities"]["str"] == 14


def test_apply_to_sheet_adds_ac_and_speed_modifiers():
    base = shm.normalize_sheet({"ac": 14, "speed": 30})
    active = [
        {"source": "Ring of Protection", "stat": "ac", "modifier": 1, "rounds_remaining": None},
        {"source": "Boots of Speed", "stat": "speed", "modifier": 30, "rounds_remaining": 5},
    ]
    effective = effects.apply_to_sheet(base, active)
    assert effective["ac"] == 15
    assert effective["speed"] == 60
    assert base["ac"] == 14 and base["speed"] == 30


def test_apply_to_sheet_stacks_multiple_effects_on_same_stat():
    base = shm.normalize_sheet({"abilities": {"str": 10}})
    active = [
        {"source": "Potion A", "stat": "str", "modifier": 2, "rounds_remaining": 5},
        {"source": "Potion B", "stat": "str", "modifier": 3, "rounds_remaining": 1},
    ]
    effective = effects.apply_to_sheet(base, active)
    assert effective["abilities"]["str"] == 15


def test_apply_to_sheet_with_no_effects_returns_equivalent_sheet():
    base = shm.normalize_sheet({"abilities": {"str": 14}, "ac": 16})
    effective = effects.apply_to_sheet(base, [])
    assert effective["abilities"] == base["abilities"]
    assert effective["ac"] == base["ac"]
