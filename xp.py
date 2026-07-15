"""XP tracking and level-up logic for D&D 5e."""

# Index N = XP required to reach level N+1 (index 0 = 0 XP = level 1).
XP_THRESHOLDS = [
    0,       # level 1
    300,     # level 2
    900,     # level 3
    2_700,   # level 4
    6_500,   # level 5
    14_000,  # level 6
    23_000,  # level 7
    34_000,  # level 8
    48_000,  # level 9
    64_000,  # level 10
    85_000,  # level 11
    100_000, # level 12
    120_000, # level 13
    140_000, # level 14
    165_000, # level 15
    195_000, # level 16
    225_000, # level 17
    265_000, # level 18
    305_000, # level 19
    355_000, # level 20
]


def level_from_xp(xp: int) -> int:
    """Return the level a character with this XP total has earned."""
    level = 1
    for i, threshold in enumerate(XP_THRESHOLDS):
        if xp >= threshold:
            level = i + 1
    return min(level, 20)


def xp_for_next_level(current_level: int) -> int | None:
    """Return the XP threshold for the next level, or None if already level 20."""
    if current_level >= 20:
        return None
    return XP_THRESHOLDS[current_level]  # thresholds[level] = start of level+1


def should_level_up(xp: int, sheet_level: int) -> bool:
    """True if earned XP qualifies the character for a higher level than they currently are."""
    return level_from_xp(xp) > sheet_level


def split_xp(total_xp: int, party_size: int) -> int:
    """Return XP per character (integer division; remainder is discarded)."""
    if party_size <= 0:
        return 0
    return total_xp // party_size
