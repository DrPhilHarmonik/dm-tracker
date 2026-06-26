import classes


def test_all_twelve_classes_present():
    assert len(classes.CLASSES) == 12


def test_spellcasting_ability_casters():
    assert classes.CLASS_SPELLCASTING_ABILITY["Bard"] == "cha"
    assert classes.CLASS_SPELLCASTING_ABILITY["Cleric"] == "wis"
    assert classes.CLASS_SPELLCASTING_ABILITY["Druid"] == "wis"
    assert classes.CLASS_SPELLCASTING_ABILITY["Paladin"] == "cha"
    assert classes.CLASS_SPELLCASTING_ABILITY["Ranger"] == "wis"
    assert classes.CLASS_SPELLCASTING_ABILITY["Sorcerer"] == "cha"
    assert classes.CLASS_SPELLCASTING_ABILITY["Warlock"] == "cha"
    assert classes.CLASS_SPELLCASTING_ABILITY["Wizard"] == "int"


def test_spellcasting_ability_non_casters_are_none():
    for cls in ["Barbarian", "Fighter", "Monk", "Rogue"]:
        assert classes.CLASS_SPELLCASTING_ABILITY[cls] is None, cls


def test_all_classes_have_primary_ability():
    for cls in classes.CLASSES:
        assert cls in classes.CLASS_PRIMARY_ABILITY, cls
        assert classes.CLASS_PRIMARY_ABILITY[cls], cls


def test_all_classes_have_proficiencies():
    for cls in classes.CLASSES:
        assert cls in classes.CLASS_PROFICIENCIES, cls
        assert len(classes.CLASS_PROFICIENCIES[cls]) > 10, cls


def test_proficiencies_content_spot_checks():
    assert "martial weapons" in classes.CLASS_PROFICIENCIES["Fighter"].lower()
    assert "light armor" in classes.CLASS_PROFICIENCIES["Rogue"].lower()
    assert "non-metal" in classes.CLASS_PROFICIENCIES["Druid"]
    assert "simple weapons" in classes.CLASS_PROFICIENCIES["Monk"].lower()
    assert "light crossbows" in classes.CLASS_PROFICIENCIES["Wizard"].lower()


def test_hit_dice_notation():
    assert classes.hit_dice_notation("Fighter", 5) == "5d10"
    assert classes.hit_dice_notation("Wizard", 1) == "1d6"
    assert classes.hit_dice_notation("Barbarian", 3) == "3d12"
    assert classes.hit_dice_notation("Unknown", 4) == "4d8"
    assert classes.hit_dice_notation("Rogue", 0) == "1d8"  # level clamped to 1


def test_every_class_has_exactly_two_saving_throws():
    for class_name in classes.CLASSES:
        assert len(classes.CLASS_SAVING_THROWS[class_name]) == 2


def test_every_class_has_a_valid_hit_die():
    for class_name in classes.CLASSES:
        assert classes.CLASS_HIT_DICE[class_name] in (6, 8, 10, 12)


def test_suggested_hp_level_one_equals_max_die_plus_con():
    assert classes.suggested_hp("Fighter", 1, 2) == 12  # d10 + 2


def test_suggested_hp_scales_with_level():
    level_1 = classes.suggested_hp("Wizard", 1, 0)
    level_5 = classes.suggested_hp("Wizard", 5, 0)
    assert level_1 == 6  # d6 max at level 1
    assert level_5 == 6 + 4 * 4  # + average-of-d6 (4) per additional level


def test_suggested_hp_never_drops_below_one():
    assert classes.suggested_hp("Wizard", 1, -10) >= 1


def test_suggested_hp_falls_back_to_d8_for_unknown_class():
    assert classes.suggested_hp("Some Homebrew Class", 1, 0) == 8
