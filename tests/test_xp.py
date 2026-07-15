import xp as xpm


def test_level_from_xp_level_1_at_zero():
    assert xpm.level_from_xp(0) == 1


def test_level_from_xp_level_2_at_threshold():
    assert xpm.level_from_xp(300) == 2


def test_level_from_xp_level_5_at_threshold():
    assert xpm.level_from_xp(6_500) == 5


def test_level_from_xp_level_5_just_below():
    assert xpm.level_from_xp(6_499) == 4


def test_level_from_xp_caps_at_20():
    assert xpm.level_from_xp(999_999) == 20


def test_xp_for_next_level_level_1():
    assert xpm.xp_for_next_level(1) == 300


def test_xp_for_next_level_level_4():
    assert xpm.xp_for_next_level(4) == 6_500


def test_xp_for_next_level_at_max_returns_none():
    assert xpm.xp_for_next_level(20) is None


def test_should_level_up_true_when_xp_exceeds_sheet_level():
    # 6500 XP qualifies for level 5, but sheet says level 4
    assert xpm.should_level_up(6_500, 4) is True


def test_should_level_up_false_when_not_enough_xp():
    assert xpm.should_level_up(1_000, 3) is False


def test_should_level_up_false_when_already_correct_level():
    assert xpm.should_level_up(900, 3) is False


def test_split_xp_even():
    assert xpm.split_xp(300, 3) == 100


def test_split_xp_truncates_remainder():
    assert xpm.split_xp(100, 3) == 33


def test_split_xp_zero_party_returns_zero():
    assert xpm.split_xp(1000, 0) == 0


def test_split_xp_zero_total():
    assert xpm.split_xp(0, 4) == 0
