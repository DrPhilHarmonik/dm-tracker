import races


def test_race_names_lists_all_thirteen_srd_entries():
    assert len(races.RACE_NAMES) == 13
    assert "Human" in races.RACE_NAMES
    assert "High Elf" in races.RACE_NAMES
    assert "Half-Elf" in races.RACE_NAMES


def test_apply_bonuses_adds_fixed_race_bonus():
    abilities = {"str": 15, "dex": 14, "con": 13, "int": 12, "wis": 10, "cha": 8}
    result = races.apply_bonuses(abilities, "High Elf")
    assert result["dex"] == 16
    assert result["int"] == 13
    assert result["str"] == 15  # untouched


def test_apply_bonuses_does_not_mutate_input():
    abilities = {"str": 15, "dex": 14, "con": 13, "int": 12, "wis": 10, "cha": 8}
    races.apply_bonuses(abilities, "High Elf")
    assert abilities["dex"] == 14


def test_apply_bonuses_unknown_race_is_a_no_op():
    abilities = {"str": 15, "dex": 14, "con": 13, "int": 12, "wis": 10, "cha": 8}
    result = races.apply_bonuses(abilities, "Not A Race")
    assert result == abilities


def test_half_elf_choice_bonus_applies_to_chosen_abilities_only():
    abilities = {"str": 8, "dex": 10, "con": 12, "int": 13, "wis": 14, "cha": 15}
    result = races.apply_bonuses(abilities, "Half-Elf", choice_abilities=["dex", "wis"])
    assert result["cha"] == 17  # fixed +2
    assert result["dex"] == 11  # chosen +1
    assert result["wis"] == 15  # chosen +1
    assert result["str"] == 8  # not chosen, untouched
    assert result["con"] == 12


def test_half_elf_choice_bonus_caps_at_two_abilities():
    abilities = {a: 10 for a in races.ABILITIES}
    # three abilities offered, only the first two (choice_bonus=2) should count
    result = races.apply_bonuses(abilities, "Half-Elf", choice_abilities=["dex", "wis", "int"])
    assert result["dex"] == 11
    assert result["wis"] == 11
    assert result["int"] == 10


def test_mountain_dwarf_has_no_choice_bonus():
    abilities = {a: 10 for a in races.ABILITIES}
    result = races.apply_bonuses(abilities, "Mountain Dwarf", choice_abilities=["dex"])
    assert result["dex"] == 10  # choice_abilities ignored since choice_bonus is 0
    assert result["str"] == 12
    assert result["con"] == 12
