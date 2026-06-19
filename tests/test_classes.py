import classes


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
