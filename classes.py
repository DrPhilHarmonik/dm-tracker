"""Reference data for 5e classes, used by the creation wizard to suggest
saving throw proficiencies and starting HP.

Skills are intentionally left unsuggested here -- 5e lets you pick N skills
from a class-specific list rather than assigning a fixed set, which is more
chargen detail than this DM tool tries to replicate. The wizard just gives
the DM a sensible saving-throw and HP starting point to edit from.
"""

CLASSES = [
    "Barbarian", "Bard", "Cleric", "Druid", "Fighter", "Monk",
    "Paladin", "Ranger", "Rogue", "Sorcerer", "Warlock", "Wizard",
]

CLASS_HIT_DICE = {
    "Barbarian": 12, "Bard": 8, "Cleric": 8, "Druid": 8, "Fighter": 10,
    "Monk": 8, "Paladin": 10, "Ranger": 10, "Rogue": 8, "Sorcerer": 6,
    "Warlock": 8, "Wizard": 6,
}

CLASS_SAVING_THROWS = {
    "Barbarian": ["str", "con"], "Bard": ["dex", "cha"], "Cleric": ["wis", "cha"],
    "Druid": ["int", "wis"], "Fighter": ["str", "con"], "Monk": ["str", "dex"],
    "Paladin": ["wis", "cha"], "Ranger": ["str", "dex"], "Rogue": ["dex", "int"],
    "Sorcerer": ["con", "cha"], "Warlock": ["wis", "cha"], "Wizard": ["int", "wis"],
}


def suggested_hp(class_name: str, level: int, con_modifier: int) -> int:
    """Average-roll HP estimate: max die at level 1, average die per level after."""
    hit_die = CLASS_HIT_DICE.get(class_name, 8)
    level = max(1, level)
    first_level = hit_die + con_modifier
    average_additional = hit_die // 2 + 1 + con_modifier
    return max(1, first_level + average_additional * (level - 1))
