"""DMG XP-budget encounter difficulty calculator (SRD math, no new data needed).

All functions are pure: they take pre-extracted CR/level lists and return a
result dict. DB access lives in the caller (screens/combat.py).
"""
import re
from fractions import Fraction
import sheet as shm

_CR_PATTERN = re.compile(r"^\s*\d+(/\d+)?\s*$")

# SRD: CR -> XP value
_CR_XP: dict[Fraction, int] = {
    Fraction(0): 10,
    Fraction(1, 8): 25,
    Fraction(1, 4): 50,
    Fraction(1, 2): 100,
    Fraction(1): 200,
    Fraction(2): 450,
    Fraction(3): 700,
    Fraction(4): 1_100,
    Fraction(5): 1_800,
    Fraction(6): 2_300,
    Fraction(7): 2_900,
    Fraction(8): 3_900,
    Fraction(9): 5_000,
    Fraction(10): 5_900,
    Fraction(11): 7_200,
    Fraction(12): 8_400,
    Fraction(13): 10_000,
    Fraction(14): 11_500,
    Fraction(15): 13_000,
    Fraction(16): 15_000,
    Fraction(17): 18_000,
    Fraction(18): 20_000,
    Fraction(19): 22_000,
    Fraction(20): 25_000,
    Fraction(21): 33_000,
    Fraction(22): 41_000,
    Fraction(23): 50_000,
    Fraction(24): 62_000,
    Fraction(25): 75_000,
    Fraction(26): 90_000,
    Fraction(27): 105_000,
    Fraction(28): 120_000,
    Fraction(29): 135_000,
    Fraction(30): 155_000,
}

# DMG: character level -> (easy, medium, hard, deadly) XP thresholds
_LEVEL_THRESHOLDS: dict[int, tuple[int, int, int, int]] = {
    1:  (25,    50,    75,    100),
    2:  (50,    100,   150,   200),
    3:  (75,    150,   225,   400),
    4:  (125,   250,   375,   500),
    5:  (250,   500,   750,   1_100),
    6:  (300,   600,   900,   1_400),
    7:  (350,   750,   1_100, 1_700),
    8:  (450,   900,   1_400, 2_100),
    9:  (550,   1_100, 1_600, 2_400),
    10: (600,   1_200, 1_900, 2_800),
    11: (800,   1_600, 2_400, 3_600),
    12: (1_000, 2_000, 3_000, 4_500),
    13: (1_100, 2_200, 3_400, 5_100),
    14: (1_250, 2_500, 3_800, 5_700),
    15: (1_400, 2_800, 4_300, 6_400),
    16: (1_600, 3_200, 4_800, 7_200),
    17: (2_000, 3_900, 5_900, 8_800),
    18: (2_100, 4_200, 6_300, 9_500),
    19: (2_400, 4_900, 7_300, 10_900),
    20: (2_800, 5_700, 8_500, 12_700),
}


def cr_xp(cr: str | None) -> int | None:
    """Return XP value for a CR string, or None if unrecognized/empty."""
    if not cr or not _CR_PATTERN.match(cr):
        return None
    value = shm.parse_cr(cr)
    return _CR_XP.get(value)


def encounter_multiplier(enemy_count: int) -> float:
    if enemy_count <= 0:
        return 1.0
    if enemy_count == 1:
        return 1.0
    if enemy_count == 2:
        return 1.5
    if enemy_count <= 6:
        return 2.0
    if enemy_count <= 10:
        return 2.5
    if enemy_count <= 14:
        return 3.0
    return 4.0


def party_thresholds(levels: list[int]) -> dict[str, int]:
    """Sum per-character thresholds across all adventurer levels."""
    easy = medium = hard = deadly = 0
    for lvl in levels:
        lvl = max(1, min(20, int(lvl or 1)))
        e, m, h, d = _LEVEL_THRESHOLDS[lvl]
        easy += e
        medium += m
        hard += h
        deadly += d
    return {"easy": easy, "medium": medium, "hard": hard, "deadly": deadly}


def calculate_difficulty(
    enemy_crs: list[str | None],
    adventurer_levels: list[int],
) -> dict:
    """Return difficulty info dict.

    enemy_crs: one entry per enemy combatant; None/empty means CR unknown.
    adventurer_levels: one entry per adventurer combatant.
    """
    if not adventurer_levels:
        return {"difficulty": "Unknown", "reason": "no adventurers", "adjusted_xp": 0,
                "raw_xp": 0, "multiplier": 1.0, "thresholds": {}, "excluded_count": 0}

    xp_values = []
    excluded = 0
    for cr in enemy_crs:
        xp = cr_xp(cr or "") if cr else None
        if xp is None:
            excluded += 1
        else:
            xp_values.append(xp)

    raw_xp = sum(xp_values)
    mult = encounter_multiplier(len(xp_values))
    adjusted_xp = int(raw_xp * mult)
    thresholds = party_thresholds(adventurer_levels)

    if not xp_values:
        difficulty = "Unknown"
    elif adjusted_xp >= thresholds["deadly"]:
        difficulty = "Deadly"
    elif adjusted_xp >= thresholds["hard"]:
        difficulty = "Hard"
    elif adjusted_xp >= thresholds["medium"]:
        difficulty = "Medium"
    elif adjusted_xp >= thresholds["easy"]:
        difficulty = "Easy"
    else:
        difficulty = "Trivial"

    return {
        "difficulty": difficulty,
        "adjusted_xp": adjusted_xp,
        "raw_xp": raw_xp,
        "multiplier": mult,
        "thresholds": thresholds,
        "excluded_count": excluded,
    }
