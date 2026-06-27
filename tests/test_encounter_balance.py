"""Tests for the DMG XP-budget encounter difficulty calculator."""
import encounter_balance as eb


def test_cr_xp_known_values():
    assert eb.cr_xp("0") == 10
    assert eb.cr_xp("1/8") == 25
    assert eb.cr_xp("1/4") == 50
    assert eb.cr_xp("1/2") == 100
    assert eb.cr_xp("1") == 200
    assert eb.cr_xp("5") == 1_800
    assert eb.cr_xp("20") == 25_000
    assert eb.cr_xp("30") == 155_000


def test_cr_xp_unknown_returns_none():
    assert eb.cr_xp("") is None
    assert eb.cr_xp("31") is None
    assert eb.cr_xp("unknown") is None
    assert eb.cr_xp(None) is None


def test_encounter_multiplier_thresholds():
    assert eb.encounter_multiplier(0) == 1.0
    assert eb.encounter_multiplier(1) == 1.0
    assert eb.encounter_multiplier(2) == 1.5
    assert eb.encounter_multiplier(3) == 2.0
    assert eb.encounter_multiplier(6) == 2.0
    assert eb.encounter_multiplier(7) == 2.5
    assert eb.encounter_multiplier(10) == 2.5
    assert eb.encounter_multiplier(11) == 3.0
    assert eb.encounter_multiplier(14) == 3.0
    assert eb.encounter_multiplier(15) == 4.0
    assert eb.encounter_multiplier(100) == 4.0


def test_party_thresholds_single_level_5():
    t = eb.party_thresholds([5])
    assert t["easy"] == 250
    assert t["medium"] == 500
    assert t["hard"] == 750
    assert t["deadly"] == 1_100


def test_party_thresholds_four_level_5s():
    t = eb.party_thresholds([5, 5, 5, 5])
    assert t["easy"] == 1_000
    assert t["medium"] == 2_000
    assert t["hard"] == 3_000
    assert t["deadly"] == 4_400


def test_party_thresholds_mixed_levels():
    t = eb.party_thresholds([1, 5, 10])
    assert t["easy"] == 25 + 250 + 600
    assert t["deadly"] == 100 + 1_100 + 2_800


def test_calculate_difficulty_trivial():
    result = eb.calculate_difficulty(["1/8"], [5])
    assert result["difficulty"] == "Trivial"
    assert result["raw_xp"] == 25
    assert result["multiplier"] == 1.0
    assert result["adjusted_xp"] == 25


def test_calculate_difficulty_deadly():
    # 7 CR 5 enemies (1800 each = 12600 raw) x2.5 multiplier = 31500 adj XP
    # Party of 4 level 5s: deadly threshold = 4400
    result = eb.calculate_difficulty(["5", "5", "5", "5", "5", "5", "5"], [5, 5, 5, 5])
    assert result["difficulty"] == "Deadly"
    assert result["raw_xp"] == 12_600
    assert result["multiplier"] == 2.5
    assert result["adjusted_xp"] == 31_500


def test_calculate_difficulty_medium():
    # 1 CR 3 enemy (700 XP) vs 4 level-3 adventurers (medium=600, hard=900)
    result = eb.calculate_difficulty(["3"], [3, 3, 3, 3])
    assert result["difficulty"] == "Medium"


def test_calculate_difficulty_no_adventurers():
    result = eb.calculate_difficulty(["5"], [])
    assert result["difficulty"] == "Unknown"
    assert result["reason"] == "no adventurers"


def test_calculate_difficulty_excludes_unknown_cr():
    result = eb.calculate_difficulty(["5", None, ""], [5, 5, 5, 5])
    assert result["excluded_count"] == 2
    # Only the CR 5 enemy counts; 1 enemy -> multiplier 1.0
    assert result["raw_xp"] == 1_800
    assert result["multiplier"] == 1.0


def test_calculate_difficulty_all_unknown_cr():
    result = eb.calculate_difficulty([None, None], [5, 5])
    assert result["difficulty"] == "Unknown"
    assert result["excluded_count"] == 2
    assert result["adjusted_xp"] == 0


def test_calculate_difficulty_thresholds_included():
    result = eb.calculate_difficulty(["1"], [5])
    assert "easy" in result["thresholds"]
    assert "deadly" in result["thresholds"]
    assert result["thresholds"]["easy"] == 250
    assert result["thresholds"]["deadly"] == 1_100


def test_calculate_difficulty_hard():
    # 2 CR 3 enemies (700 each = 1400 raw) x1.5 = 2100 adj XP
    # Party of 4 level-5s: hard=3000, deadly=4400; medium=2000
    # 2100 is >= hard? No: hard for 4 level-5s = 3000. 2100 < 3000, >= medium (2000). Should be Medium.
    # Let's try 3 CR 3 enemies: 2100 raw x2.0 = 4200 adj XP >= hard(3000) but < deadly(4400). Hard.
    result = eb.calculate_difficulty(["3", "3", "3"], [5, 5, 5, 5])
    assert result["difficulty"] == "Hard"
    assert result["raw_xp"] == 2_100
    assert result["multiplier"] == 2.0
    assert result["adjusted_xp"] == 4_200


def test_level_clamped_to_valid_range():
    # level 0 should be treated as 1, level 99 as 20
    t_low = eb.party_thresholds([0])
    t_one = eb.party_thresholds([1])
    assert t_low == t_one

    t_high = eb.party_thresholds([99])
    t_twenty = eb.party_thresholds([20])
    assert t_high == t_twenty
