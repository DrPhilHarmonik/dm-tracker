"""Reference data for 5e classes, used by the creation wizard to suggest
saving throw proficiencies, starting HP, armor/weapon proficiencies, and
(for spellcasters) which ability drives spell attacks and save DCs.

Skills are intentionally left unsuggested here -- 5e lets you pick N skills
from a class-specific list rather than assigning a fixed set, which is more
chargen detail than this DM tool tries to replicate.
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

# None = not a spellcaster (base class; subclasses like Eldritch Knight are
# out of scope and handled via the freeform subclass notes field).
CLASS_SPELLCASTING_ABILITY: dict[str, str | None] = {
    "Barbarian": None, "Bard": "cha", "Cleric": "wis", "Druid": "wis",
    "Fighter": None, "Monk": None, "Paladin": "cha", "Ranger": "wis",
    "Rogue": None, "Sorcerer": "cha", "Warlock": "cha", "Wizard": "int",
}

# Display hint shown during Standard Array assignment. Multi-option classes
# show both so the DM can make an informed assignment.
CLASS_PRIMARY_ABILITY: dict[str, str] = {
    "Barbarian": "str", "Bard": "cha", "Cleric": "wis", "Druid": "wis",
    "Fighter": "str or dex", "Monk": "dex", "Paladin": "str",
    "Ranger": "dex", "Rogue": "dex", "Sorcerer": "cha",
    "Warlock": "cha", "Wizard": "int",
}

# Short SRD-accurate armor/weapon proficiency summaries, baked into
# sheet["proficiencies"] at character creation.
CLASS_PROFICIENCIES: dict[str, str] = {
    "Barbarian": "Light armor, medium armor, shields; simple weapons, martial weapons",
    "Bard": "Light armor; simple weapons, hand crossbows, longswords, rapiers, shortswords",
    "Cleric": "Light armor, medium armor, shields; simple weapons",
    "Druid": "Light armor, medium armor, shields (non-metal); clubs, daggers, darts, javelins, maces, quarterstaffs, scimitars, sickles, slings, spears",
    "Fighter": "All armor, shields; simple weapons, martial weapons",
    "Monk": "Simple weapons, shortswords",
    "Paladin": "All armor, shields; simple weapons, martial weapons",
    "Ranger": "Light armor, medium armor, shields; simple weapons, martial weapons",
    "Rogue": "Light armor; simple weapons, hand crossbows, longswords, rapiers, shortswords",
    "Sorcerer": "Daggers, darts, slings, quarterstaffs, light crossbows",
    "Warlock": "Light armor; simple weapons",
    "Wizard": "Daggers, darts, slings, quarterstaffs, light crossbows",
}


def suggested_hp(class_name: str, level: int, con_modifier: int) -> int:
    """Average-roll HP: max die at level 1, average die per level after."""
    hit_die = CLASS_HIT_DICE.get(class_name, 8)
    level = max(1, level)
    first_level = hit_die + con_modifier
    average_additional = hit_die // 2 + 1 + con_modifier
    return max(1, first_level + average_additional * (level - 1))


def hit_dice_notation(class_name: str, level: int) -> str:
    """e.g. '5d10' for a level-5 Fighter."""
    die = CLASS_HIT_DICE.get(class_name, 8)
    return f"{max(1, level)}d{die}"
