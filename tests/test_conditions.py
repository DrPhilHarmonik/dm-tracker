import conditions as cnd
import combat


def test_fifteen_conditions_present():
    assert len(cnd.CONDITIONS) == 15


def test_condition_names_matches_keys():
    assert cnd.CONDITION_NAMES == list(cnd.CONDITIONS.keys())


def test_all_conditions_have_non_empty_description():
    for name, desc in cnd.CONDITIONS.items():
        assert desc.strip(), f"{name} has empty description"
        assert len(desc) > 10, f"{name} description too short"


def test_spot_check_conditions():
    assert "advantage" in cnd.CONDITIONS["Blinded"].lower()
    assert "STR" in cnd.CONDITIONS["Paralyzed"]
    assert "DEX" in cnd.CONDITIONS["Paralyzed"]
    assert "speed" in cnd.CONDITIONS["Grappled"].lower()
    assert "action" in cnd.CONDITIONS["Incapacitated"].lower()
    assert "prone" in cnd.CONDITIONS["Unconscious"].lower()


def test_known_condition_names_are_present():
    expected = [
        "Blinded", "Charmed", "Deafened", "Exhaustion", "Frightened",
        "Grappled", "Incapacitated", "Invisible", "Paralyzed", "Petrified",
        "Poisoned", "Prone", "Restrained", "Stunned", "Unconscious",
    ]
    for name in expected:
        assert name in cnd.CONDITIONS, f"Missing condition: {name}"


def test_add_death_save_success_resolves_at_three():
    c = combat.normalize_combat({"combatants": [{"entity_id": 1}]})
    c, res = combat.add_death_save(c, 1, success=True)
    assert res is None
    assert c["combatants"][0]["death_saves"]["successes"] == 1
    c, res = combat.add_death_save(c, 1, success=True)
    assert res is None
    c, res = combat.add_death_save(c, 1, success=True)
    assert res == "stable"


def test_add_death_save_failure_resolves_at_three():
    c = combat.normalize_combat({"combatants": [{"entity_id": 1}]})
    c, _ = combat.add_death_save(c, 1, success=False)
    c, _ = combat.add_death_save(c, 1, success=False)
    c, res = combat.add_death_save(c, 1, success=False)
    assert res == "dead"


def test_death_save_counts_are_independent():
    c = combat.normalize_combat({"combatants": [{"entity_id": 1}]})
    c, _ = combat.add_death_save(c, 1, success=True)
    c, _ = combat.add_death_save(c, 1, success=False)
    saves = c["combatants"][0]["death_saves"]
    assert saves["successes"] == 1
    assert saves["failures"] == 1


def test_reset_death_saves():
    c = combat.normalize_combat({"combatants": [{"entity_id": 1}]})
    c, _ = combat.add_death_save(c, 1, success=True)
    c, _ = combat.add_death_save(c, 1, success=False)
    c = combat.reset_death_saves(c, 1)
    saves = c["combatants"][0]["death_saves"]
    assert saves == {"successes": 0, "failures": 0}


def test_death_saves_capped_at_three():
    raw = {"combatants": [{"entity_id": 1, "death_saves": {"successes": 99, "failures": 99}}]}
    c = combat.normalize_combat(raw)
    saves = c["combatants"][0]["death_saves"]
    assert saves["successes"] == 3
    assert saves["failures"] == 3


def test_normalize_combat_old_data_gets_zero_death_saves():
    """Old combatant records without death_saves still normalize cleanly."""
    raw = {"combatants": [{"entity_id": 5, "initiative": 12, "conditions": []}]}
    c = combat.normalize_combat(raw)
    assert c["combatants"][0]["death_saves"] == {"successes": 0, "failures": 0}
