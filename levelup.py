"""Level-up logic for D&D 5e adventurers.

Handles three mechanical changes on level-up:
  - Level increment + proficiency bonus recalculation
  - HP maximum increase (rolled or average)
  - Spell slot maximum update (full casters, half casters, Warlock pact magic)

Class features are surfaced as text reminders only -- the DM applies them.
"""
import sheet as shm
import classes as cls_mod

# Standard spell slot tables (level → {slot_level: max_count}).
# Keys are only the levels that have slots; levels with no slots are absent.

_FULL_CASTER_SLOTS = {
    1:  {1: 2},
    2:  {1: 3},
    3:  {1: 4, 2: 2},
    4:  {1: 4, 2: 3},
    5:  {1: 4, 2: 3, 3: 2},
    6:  {1: 4, 2: 3, 3: 3},
    7:  {1: 4, 2: 3, 3: 3, 4: 1},
    8:  {1: 4, 2: 3, 3: 3, 4: 2},
    9:  {1: 4, 2: 3, 3: 3, 4: 3, 5: 1},
    10: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2},
    11: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1},
    12: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1},
    13: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1},
    14: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1},
    15: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1},
    16: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1},
    17: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1, 9: 1},
    18: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 1, 7: 1, 8: 1, 9: 1},
    19: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 1, 8: 1, 9: 1},
    20: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 2, 8: 1, 9: 1},
}

_HALF_CASTER_SLOTS = {
    2:  {1: 2},
    3:  {1: 3},
    4:  {1: 3},
    5:  {1: 4, 2: 2},
    6:  {1: 4, 2: 2},
    7:  {1: 4, 2: 3},
    8:  {1: 4, 2: 3},
    9:  {1: 4, 2: 3, 3: 2},
    10: {1: 4, 2: 3, 3: 2},
    11: {1: 4, 2: 3, 3: 3},
    12: {1: 4, 2: 3, 3: 3},
    13: {1: 4, 2: 3, 3: 3, 4: 1},
    14: {1: 4, 2: 3, 3: 3, 4: 1},
    15: {1: 4, 2: 3, 3: 3, 4: 2},
    16: {1: 4, 2: 3, 3: 3, 4: 2},
    17: {1: 4, 2: 3, 3: 3, 4: 3, 5: 1},
    18: {1: 4, 2: 3, 3: 3, 4: 3, 5: 1},
    19: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2},
    20: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2},
}

# Warlock pact magic: all slots are at one level, count varies.
_WARLOCK_SLOTS = {
    1:  {1: 1}, 2: {1: 2},
    3:  {2: 2}, 4: {2: 2},
    5:  {3: 2}, 6: {3: 2},
    7:  {4: 2}, 8: {4: 2},
    9:  {5: 2}, 10: {5: 2},
    11: {5: 3}, 12: {5: 3}, 13: {5: 3}, 14: {5: 3}, 15: {5: 3},
    16: {5: 3}, 17: {5: 4}, 18: {5: 4}, 19: {5: 4}, 20: {5: 4},
}

_FULL_CASTERS = {"Bard", "Cleric", "Druid", "Sorcerer", "Wizard"}
_HALF_CASTERS = {"Paladin", "Ranger"}

# Notable class features per level (text only -- DM applies them).
CLASS_FEATURES: dict[str, dict[int, str]] = {
    "Barbarian": {
        2: "Reckless Attack, Danger Sense",
        3: "Primal Path",
        4: "Ability Score Improvement",
        5: "Extra Attack, Fast Movement",
        6: "Path Feature",
        7: "Feral Instinct",
        8: "Ability Score Improvement",
        9: "Brutal Critical (1 die)",
        10: "Path Feature",
        11: "Relentless Rage",
        12: "Ability Score Improvement",
        13: "Brutal Critical (2 dice)",
        14: "Path Feature",
        15: "Persistent Rage",
        16: "Ability Score Improvement",
        17: "Brutal Critical (3 dice)",
        18: "Indomitable Might",
        19: "Ability Score Improvement",
        20: "Primal Champion (+4 STR, +4 CON)",
    },
    "Bard": {
        2: "Jack of All Trades, Song of Rest (d6)",
        3: "Bard College, Expertise",
        4: "Ability Score Improvement",
        5: "Bardic Inspiration (d8), Font of Inspiration",
        6: "Countercharm, College Feature",
        7: "—",
        8: "Ability Score Improvement",
        9: "Song of Rest (d8)",
        10: "Bardic Inspiration (d10), Expertise, Magical Secrets",
        11: "—",
        12: "Ability Score Improvement",
        13: "Song of Rest (d10)",
        14: "Magical Secrets, College Feature",
        15: "Bardic Inspiration (d12)",
        16: "Ability Score Improvement",
        17: "Song of Rest (d12)",
        18: "Magical Secrets",
        19: "Ability Score Improvement",
        20: "Superior Inspiration",
    },
    "Cleric": {
        2: "Channel Divinity (1/rest), Divine Domain Feature",
        3: "—",
        4: "Ability Score Improvement",
        5: "Destroy Undead (CR 1/2)",
        6: "Channel Divinity (2/rest), Divine Domain Feature",
        7: "—",
        8: "Ability Score Improvement, Destroy Undead (CR 1), Divine Domain Feature",
        9: "—",
        10: "Divine Intervention",
        11: "Destroy Undead (CR 2)",
        12: "Ability Score Improvement",
        13: "—",
        14: "Destroy Undead (CR 3)",
        15: "—",
        16: "Ability Score Improvement",
        17: "Destroy Undead (CR 4), Divine Domain Feature",
        18: "Channel Divinity (3/rest)",
        19: "Ability Score Improvement",
        20: "Divine Intervention improvement",
    },
    "Druid": {
        2: "Wild Shape (CR 1/4), Druid Circle",
        3: "—",
        4: "Wild Shape (CR 1/2, swim), Ability Score Improvement",
        5: "—",
        6: "Circle Feature",
        7: "—",
        8: "Wild Shape (CR 1, fly), Ability Score Improvement",
        9: "—",
        10: "Circle Feature",
        11: "—",
        12: "Ability Score Improvement",
        13: "—",
        14: "Circle Feature",
        15: "—",
        16: "Ability Score Improvement",
        17: "—",
        18: "Timeless Body, Beast Spells",
        19: "Ability Score Improvement",
        20: "Archdruid",
    },
    "Fighter": {
        2: "Action Surge (1/rest)",
        3: "Martial Archetype",
        4: "Ability Score Improvement",
        5: "Extra Attack",
        6: "Ability Score Improvement",
        7: "Archetype Feature",
        8: "Ability Score Improvement",
        9: "Indomitable (1/rest)",
        10: "Archetype Feature",
        11: "Extra Attack (2)",
        12: "Ability Score Improvement",
        13: "Indomitable (2/rest)",
        14: "Ability Score Improvement",
        15: "Archetype Feature",
        16: "Ability Score Improvement",
        17: "Action Surge (2/rest), Indomitable (3/rest)",
        18: "Archetype Feature",
        19: "Ability Score Improvement",
        20: "Extra Attack (3)",
    },
    "Monk": {
        2: "Ki (2 points), Unarmored Movement (+10 ft.), Flurry of Blows, Patient Defense, Step of the Wind",
        3: "Monastic Tradition, Deflect Missiles",
        4: "Ability Score Improvement, Slow Fall",
        5: "Extra Attack, Stunning Strike",
        6: "Ki-Empowered Strikes, Tradition Feature",
        7: "Evasion, Stillness of Mind",
        8: "Ability Score Improvement",
        9: "Unarmored Movement improvement",
        10: "Purity of Body",
        11: "Tradition Feature",
        12: "Ability Score Improvement",
        13: "Tongue of the Sun and Moon",
        14: "Diamond Soul",
        15: "Timeless Body",
        16: "Ability Score Improvement",
        17: "Tradition Feature",
        18: "Empty Body",
        19: "Ability Score Improvement",
        20: "Perfect Self",
    },
    "Paladin": {
        2: "Fighting Style, Spellcasting, Divine Smite",
        3: "Divine Health, Sacred Oath",
        4: "Ability Score Improvement",
        5: "Extra Attack",
        6: "Aura of Protection",
        7: "Sacred Oath Feature",
        8: "Ability Score Improvement",
        9: "—",
        10: "Aura of Courage",
        11: "Improved Divine Smite",
        12: "Ability Score Improvement",
        13: "—",
        14: "Cleansing Touch",
        15: "Sacred Oath Feature",
        16: "Ability Score Improvement",
        17: "—",
        18: "Aura improvements",
        19: "Ability Score Improvement",
        20: "Sacred Oath Feature",
    },
    "Ranger": {
        2: "Fighting Style, Spellcasting",
        3: "Ranger Archetype, Primeval Awareness",
        4: "Ability Score Improvement",
        5: "Extra Attack",
        6: "Favored Enemy and Natural Explorer improvements",
        7: "Archetype Feature",
        8: "Ability Score Improvement, Land's Stride",
        9: "—",
        10: "Natural Explorer improvement, Hide in Plain Sight",
        11: "Archetype Feature",
        12: "Ability Score Improvement",
        13: "—",
        14: "Favored Enemy improvement, Vanish",
        15: "Archetype Feature",
        16: "Ability Score Improvement",
        17: "—",
        18: "Feral Senses",
        19: "Ability Score Improvement",
        20: "Foe Slayer",
    },
    "Rogue": {
        2: "Cunning Action",
        3: "Roguish Archetype",
        4: "Ability Score Improvement",
        5: "Uncanny Dodge",
        6: "Expertise",
        7: "Evasion",
        8: "Ability Score Improvement",
        9: "Archetype Feature",
        10: "Ability Score Improvement",
        11: "Reliable Talent",
        12: "Ability Score Improvement",
        13: "Archetype Feature",
        14: "Blindsense",
        15: "Slippery Mind",
        16: "Ability Score Improvement",
        17: "Archetype Feature",
        18: "Elusive",
        19: "Ability Score Improvement",
        20: "Stroke of Luck",
    },
    "Sorcerer": {
        2: "Font of Magic, Sorcery Points (2)",
        3: "Metamagic (2 options)",
        4: "Ability Score Improvement",
        5: "—",
        6: "Sorcerous Origin Feature",
        7: "—",
        8: "Ability Score Improvement",
        9: "—",
        10: "Metamagic (3 options)",
        11: "—",
        12: "Ability Score Improvement",
        13: "—",
        14: "Sorcerous Origin Feature",
        15: "—",
        16: "Ability Score Improvement",
        17: "Metamagic (4 options)",
        18: "Sorcerous Origin Feature",
        19: "Ability Score Improvement",
        20: "Sorcerous Restoration",
    },
    "Warlock": {
        2: "Eldritch Invocations (2)",
        3: "Pact Boon",
        4: "Ability Score Improvement",
        5: "—",
        6: "Otherworldly Patron Feature",
        7: "—",
        8: "Ability Score Improvement",
        9: "—",
        10: "Otherworldly Patron Feature",
        11: "Mystic Arcanum (6th level)",
        12: "Ability Score Improvement",
        13: "Mystic Arcanum (7th level)",
        14: "Otherworldly Patron Feature",
        15: "Mystic Arcanum (8th level)",
        16: "Ability Score Improvement",
        17: "Mystic Arcanum (9th level)",
        18: "—",
        19: "Ability Score Improvement",
        20: "Eldritch Master",
    },
    "Wizard": {
        2: "Arcane Tradition",
        3: "—",
        4: "Ability Score Improvement",
        5: "—",
        6: "Arcane Tradition Feature",
        7: "—",
        8: "Ability Score Improvement",
        9: "—",
        10: "Arcane Tradition Feature",
        11: "—",
        12: "Ability Score Improvement",
        13: "—",
        14: "Arcane Tradition Feature",
        15: "—",
        16: "Ability Score Improvement",
        17: "—",
        18: "Spell Mastery",
        19: "Ability Score Improvement",
        20: "Signature Spells",
    },
}


def slot_table(class_name: str) -> dict[int, dict[int, int]]:
    """Return the full slot table for a class (level → {slot_level: max_count}).
    Returns {} for non-casters."""
    if class_name in _FULL_CASTERS:
        return _FULL_CASTER_SLOTS
    if class_name == "Warlock":
        return _WARLOCK_SLOTS
    if class_name in _HALF_CASTERS:
        return _HALF_CASTER_SLOTS
    return {}


def average_hp_gain(class_name: str, con_modifier: int) -> int:
    """HP gained by taking average on a level-up (hit die / 2 + 1 + CON mod)."""
    hit_die = cls_mod.CLASS_HIT_DICE.get(class_name, 8)
    return max(1, hit_die // 2 + 1 + con_modifier)


def apply_level_up(sheet: dict, class_name: str, hp_gain: int) -> dict:
    """Return a new sheet dict with level incremented, HP max increased,
    and spell slots updated to the new level's maximums.

    hp_gain is the raw die roll or average result for the new level, already
    clamped to at least 1 by the caller.
    """
    sheet = dict(sheet)
    new_level = min(20, int(sheet.get("level") or 1) + 1)
    sheet["level"] = new_level
    sheet["hp_max"] = int(sheet.get("hp_max") or 0) + max(1, hp_gain)
    sheet["hit_dice"] = cls_mod.hit_dice_notation(class_name, new_level)

    # Update spell slot maximums, increasing current by the delta gained.
    table = slot_table(class_name)
    old_slots = {int(k): v for k, v in (sheet.get("spell_slots") or {}).items()}
    new_maxes = table.get(new_level, {})

    spell_slots = {}
    for lvl in range(1, 10):
        old_max = (old_slots.get(lvl) or {}).get("max", 0)
        old_cur = (old_slots.get(lvl) or {}).get("current", 0)
        # For casters with a slot table, absent entries in the new level mean
        # 0 slots (Warlock pact magic shifts slot levels this way).
        # For non-casters (empty table) keep old_max (already 0).
        new_max = new_maxes.get(lvl, 0) if table else old_max
        delta = max(0, new_max - old_max)
        spell_slots[str(lvl)] = {
            "max": new_max,
            "current": min(new_max, old_cur + delta),
        }
    sheet["spell_slots"] = spell_slots

    return shm.normalize_sheet(sheet)


def features_at_level(class_name: str, level: int) -> str:
    """Return the feature summary for a class at a given level, or '' if none."""
    return CLASS_FEATURES.get(class_name, {}).get(level, "")
