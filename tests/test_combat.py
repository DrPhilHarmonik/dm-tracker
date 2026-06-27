import combat


def test_add_combatant_is_idempotent():
    state = combat.default_combat()
    state = combat.add_combatant(state, 1)
    state = combat.add_combatant(state, 1)
    assert [c["entity_id"] for c in state["combatants"]] == [1]


def test_remove_combatant_resets_when_empty():
    state = combat.default_combat()
    state = combat.add_combatant(state, 1)
    state = combat.remove_combatant(state, 1)
    assert state["combatants"] == []
    assert state["turn_index"] == 0
    assert state["started"] is False


def test_remove_combatant_clamps_turn_index():
    state = combat.default_combat()
    for entity_id in (1, 2, 3):
        state = combat.add_combatant(state, entity_id)
    state = combat.start_encounter(state)
    state["turn_index"] = 2
    state = combat.remove_combatant(state, 3)
    assert state["turn_index"] == 0


def test_set_initiative_updates_matching_combatant():
    state = combat.default_combat()
    state = combat.add_combatant(state, 1)
    state = combat.add_combatant(state, 2)
    state = combat.set_initiative(state, 2, 17)
    by_id = {c["entity_id"]: c["initiative"] for c in state["combatants"]}
    assert by_id == {1: 0, 2: 17}


def test_start_encounter_sorts_by_initiative_desc():
    state = combat.default_combat()
    for entity_id in (1, 2, 3):
        state = combat.add_combatant(state, entity_id)
    state = combat.set_initiative(state, 1, 5)
    state = combat.set_initiative(state, 2, 20)
    state = combat.set_initiative(state, 3, 12)
    state = combat.start_encounter(state)
    assert [c["entity_id"] for c in state["combatants"]] == [2, 3, 1]
    assert state["started"] is True
    assert state["round"] == 1
    assert state["turn_index"] == 0


def test_next_turn_advances_without_wrapping():
    state = combat.default_combat()
    for entity_id in (1, 2):
        state = combat.add_combatant(state, entity_id)
    state = combat.start_encounter(state)
    state = combat.next_turn(state)
    assert state["turn_index"] == 1
    assert state["round"] == 1


def test_next_turn_wraps_and_advances_round():
    state = combat.default_combat()
    for entity_id in (1, 2):
        state = combat.add_combatant(state, entity_id)
    state = combat.start_encounter(state)
    state = combat.next_turn(state)
    state = combat.next_turn(state)
    assert state["turn_index"] == 0
    assert state["round"] == 2


def test_next_turn_ticks_and_expires_conditions_on_round_wrap():
    state = combat.default_combat()
    state = combat.add_combatant(state, 1)
    state = combat.add_condition(state, 1, "Prone", 1)
    state = combat.add_condition(state, 1, "Blessed", None)
    state = combat.start_encounter(state)
    state = combat.next_turn(state)  # only one combatant -> wraps immediately
    conditions = state["combatants"][0]["conditions"]
    assert [c["name"] for c in conditions] == ["Blessed"]


def test_next_round_skips_remaining_turns_and_ticks_conditions():
    state = combat.default_combat()
    for entity_id in (1, 2, 3):
        state = combat.add_combatant(state, entity_id)
    state = combat.add_condition(state, 1, "Stunned", 1)
    state = combat.start_encounter(state)
    state["turn_index"] = 1
    state = combat.next_round(state)
    assert state["turn_index"] == 0
    assert state["round"] == 2
    assert state["combatants"][0]["conditions"] == []


def test_current_combatant_returns_none_when_empty():
    assert combat.current_combatant(combat.default_combat()) is None


def test_current_combatant_matches_turn_index():
    state = combat.default_combat()
    for entity_id in (1, 2, 3):
        state = combat.add_combatant(state, entity_id)
    state = combat.start_encounter(state)
    state = combat.next_turn(state)
    assert combat.current_combatant(state)["entity_id"] == state["combatants"][1]["entity_id"]


def test_add_and_remove_condition():
    state = combat.default_combat()
    state = combat.add_combatant(state, 1)
    state = combat.add_condition(state, 1, "Prone", None)
    state = combat.add_condition(state, 1, "Stunned", 2)
    assert len(state["combatants"][0]["conditions"]) == 2
    state = combat.remove_condition(state, 1, 0)
    assert [c["name"] for c in state["combatants"][0]["conditions"]] == ["Stunned"]


def test_apply_damage_clamps_at_zero():
    assert combat.apply_damage(10, 15) == 0
    assert combat.apply_damage(10, 4) == 6


def test_apply_heal_clamps_at_max():
    assert combat.apply_heal(10, 20, 5) == 15
    assert combat.apply_heal(18, 20, 50) == 20


def test_normalize_combat_fills_defaults_for_missing_data():
    normalized = combat.normalize_combat(None)
    assert normalized == combat.default_combat()

    partial = combat.normalize_combat({"combatants": [{"entity_id": "7"}]})
    assert partial["combatants"] == [
        {"entity_id": 7, "initiative": 0, "conditions": [], "death_saves": {"successes": 0, "failures": 0}}
    ]
