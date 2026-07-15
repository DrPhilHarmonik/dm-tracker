import srd


def test_all_monsters_have_required_keys():
    required = {"name", "cr", "creature_type", "ac", "hp_max", "abilities", "attacks"}
    for m in srd.MONSTERS:
        missing = required - m.keys()
        assert not missing, f"{m['name']} missing keys: {missing}"


def test_abilities_have_all_six_scores():
    for m in srd.MONSTERS:
        for stat in ("str", "dex", "con", "int", "wis", "cha"):
            assert stat in m["abilities"], f"{m['name']} missing ability {stat}"


def test_search_empty_returns_all():
    assert srd.search("") == srd.MONSTERS


def test_search_by_name():
    results = srd.search("goblin")
    assert any(m["name"] == "Goblin" for m in results)


def test_search_by_name_case_insensitive():
    results = srd.search("TROLL")
    assert any(m["name"] == "Troll" for m in results)


def test_search_by_cr():
    results = srd.search("1/4")
    crs = {m["cr"] for m in results}
    assert "1/4" in crs
    assert all(m["cr"] == "1/4" for m in results)


def test_search_no_match_returns_empty():
    assert srd.search("xyzzy") == []


def test_find_exact_name():
    m = srd.find("Vampire")
    assert m is not None
    assert m["name"] == "Vampire"


def test_find_case_insensitive():
    m = srd.find("lich")
    assert m is not None
    assert m["name"] == "Lich"


def test_find_no_match_returns_none():
    assert srd.find("Beholder") is None


def test_wizard_prefill_has_expected_keys():
    m = srd.find("Goblin")
    prefill = srd.wizard_prefill(m)
    for key in ("name", "cr", "creature_type", "ac", "hp_max", "abilities",
                "attacks", "special_abilities", "resistances", "immunities",
                "vulnerabilities", "saving_throw_proficiencies", "skill_proficiencies"):
        assert key in prefill, f"wizard_prefill missing key: {key}"


def test_wizard_prefill_does_not_mutate_source():
    m = srd.find("Orc")
    original_attacks = list(m["attacks"])
    prefill = srd.wizard_prefill(m)
    prefill["attacks"].append({"name": "Extra", "bonus": "+0", "damage": "1d4", "action_cost": "action"})
    assert m["attacks"] == original_attacks


def test_monster_count_reasonable():
    assert len(srd.MONSTERS) >= 30
