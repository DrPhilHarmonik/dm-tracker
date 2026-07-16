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


def test_monster_count_full_srd():
    assert len(srd.MONSTERS) >= 300


def test_adult_red_dragon_stats():
    m = srd.find("Adult Red Dragon")
    assert m is not None
    assert m["cr"] == "17"
    assert m["ac"] == 19
    assert m["hp_max"] == 256
    assert m["creature_type"] == "Dragon"


def test_aboleth_stats():
    m = srd.find("Aboleth")
    assert m is not None
    assert m["cr"] == "10"
    assert m["ac"] == 17
    assert m["hp_max"] == 135


def test_lich_stats():
    m = srd.find("Lich")
    assert m is not None
    assert m["cr"] == "21"
    assert m["ac"] == 17
    assert m["hp_max"] == 135


def test_fire_breath_not_in_attacks():
    """Breath weapons (saving throw, not attack roll) should be in specials, not attacks."""
    m = srd.find("Adult Red Dragon")
    assert m is not None
    attack_names = {a["name"] for a in m["attacks"]}
    assert not any("breath" in n.lower() for n in attack_names)
    special_names = {s["name"] for s in m["special_abilities"]}
    assert any("breath" in n.lower() for n in special_names)


def test_search_returns_multiple_dragons():
    results = srd.search("dragon")
    assert len(results) >= 5


def test_all_attacks_have_bonus_field():
    for m in srd.MONSTERS:
        for a in m.get("attacks", []):
            assert "bonus" in a, f"{m['name']} attack '{a.get('name')}' missing bonus"
