import sheet


def test_ability_modifier_matches_5e_table():
    assert sheet.ability_modifier(1) == -5
    assert sheet.ability_modifier(8) == -1
    assert sheet.ability_modifier(9) == -1
    assert sheet.ability_modifier(10) == 0
    assert sheet.ability_modifier(11) == 0
    assert sheet.ability_modifier(15) == 2
    assert sheet.ability_modifier(20) == 5


def test_proficiency_bonus_for_level_brackets():
    assert sheet.proficiency_bonus_for_level(1) == 2
    assert sheet.proficiency_bonus_for_level(4) == 2
    assert sheet.proficiency_bonus_for_level(5) == 3
    assert sheet.proficiency_bonus_for_level(8) == 3
    assert sheet.proficiency_bonus_for_level(9) == 4
    assert sheet.proficiency_bonus_for_level(13) == 5
    assert sheet.proficiency_bonus_for_level(17) == 6
    assert sheet.proficiency_bonus_for_level(20) == 6


def test_proficiency_bonus_for_cr_brackets():
    assert sheet.proficiency_bonus_for_cr("0") == 2
    assert sheet.proficiency_bonus_for_cr("1/8") == 2
    assert sheet.proficiency_bonus_for_cr("1/4") == 2
    assert sheet.proficiency_bonus_for_cr("1/2") == 2
    assert sheet.proficiency_bonus_for_cr("4") == 2
    assert sheet.proficiency_bonus_for_cr("5") == 3
    assert sheet.proficiency_bonus_for_cr("17") == 6
    assert sheet.proficiency_bonus_for_cr("30") == 9


def test_normalize_sheet_fills_missing_keys():
    normalized = sheet.normalize_sheet(None)
    assert normalized["abilities"] == {a: 10 for a in sheet.ABILITIES}
    assert normalized["attacks"] == []

    partial = sheet.normalize_sheet({"abilities": {"str": 18}, "ac": 15})
    assert partial["abilities"]["str"] == 18
    assert partial["abilities"]["dex"] == 10
    assert partial["ac"] == 15


def test_saving_throw_bonus_applies_proficiency():
    s = sheet.normalize_sheet({
        "abilities": {"str": 16},
        "saving_throw_proficiencies": ["str"],
    })
    pb = sheet.proficiency_bonus_for_level(5)
    assert sheet.saving_throw_bonus(s, "str", pb) == 3 + pb
    assert sheet.saving_throw_bonus(s, "dex", pb) == 0


def test_skill_bonus_proficient_and_expertise():
    s = sheet.normalize_sheet({
        "abilities": {"dex": 18},
        "skill_proficiencies": {"stealth": "expertise", "acrobatics": "proficient"},
    })
    pb = sheet.proficiency_bonus_for_level(5)
    assert sheet.skill_bonus(s, "stealth", pb) == 4 + pb * 2
    assert sheet.skill_bonus(s, "acrobatics", pb) == 4 + pb
    assert sheet.skill_bonus(s, "sleight_of_hand", pb) == 4


def test_proficiency_bonus_dispatches_on_entity_type():
    adventurer_sheet = sheet.normalize_sheet({"level": 9})
    enemy_sheet = sheet.normalize_sheet({"cr": "9"})
    assert sheet.proficiency_bonus("adventurer", adventurer_sheet) == 4
    assert sheet.proficiency_bonus("enemy", enemy_sheet) == 4
