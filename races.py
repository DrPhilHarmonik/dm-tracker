"""Reference data for SRD-legal 5e races, used by the creation wizard to
bake ability score / speed / senses / language bonuses into an Adventurer
at creation time.

Subraces that always grant a fixed ability bonus (Elf, Dwarf, Halfling,
Gnome) are listed as their own flat entries (e.g. "High Elf") rather than a
two-tier race-then-subrace pick, since the SRD requires picking a subrace
for those anyway. Bonuses are baked into the Standard Array once, at
character creation -- nothing here is re-applied later, so changing a
character's race after creation is a manual edit, same as today.
"""

ABILITIES = ["str", "dex", "con", "int", "wis", "cha"]

RACES: dict[str, dict] = {
    "Human": {
        "ability_bonuses": {"str": 1, "dex": 1, "con": 1, "int": 1, "wis": 1, "cha": 1},
        "speed": 30, "senses": "", "languages": "Common, one extra language of your choice",
        "choice_bonus": 0,
    },
    "High Elf": {
        "ability_bonuses": {"dex": 2, "int": 1},
        "speed": 30, "senses": "Darkvision 60 ft.", "languages": "Common, Elvish",
        "choice_bonus": 0,
    },
    "Wood Elf": {
        "ability_bonuses": {"dex": 2, "wis": 1},
        "speed": 35, "senses": "Darkvision 60 ft.", "languages": "Common, Elvish",
        "choice_bonus": 0,
    },
    "Hill Dwarf": {
        "ability_bonuses": {"con": 2, "wis": 1},
        "speed": 25, "senses": "Darkvision 60 ft.", "languages": "Common, Dwarvish",
        "choice_bonus": 0,
    },
    "Mountain Dwarf": {
        "ability_bonuses": {"con": 2, "str": 2},
        "speed": 25, "senses": "Darkvision 60 ft.", "languages": "Common, Dwarvish",
        "choice_bonus": 0,
    },
    "Lightfoot Halfling": {
        "ability_bonuses": {"dex": 2, "cha": 1},
        "speed": 25, "senses": "", "languages": "Common, Halfling",
        "choice_bonus": 0,
    },
    "Stout Halfling": {
        "ability_bonuses": {"dex": 2, "con": 1},
        "speed": 25, "senses": "", "languages": "Common, Halfling",
        "choice_bonus": 0,
    },
    "Forest Gnome": {
        "ability_bonuses": {"int": 2, "dex": 1},
        "speed": 25, "senses": "Darkvision 60 ft.", "languages": "Common, Gnomish",
        "choice_bonus": 0,
    },
    "Rock Gnome": {
        "ability_bonuses": {"int": 2, "con": 1},
        "speed": 25, "senses": "Darkvision 60 ft.", "languages": "Common, Gnomish",
        "choice_bonus": 0,
    },
    "Half-Elf": {
        "ability_bonuses": {"cha": 2},
        "speed": 30, "senses": "Darkvision 60 ft.",
        "languages": "Common, Elvish, one extra language of your choice",
        "choice_bonus": 2,
    },
    "Half-Orc": {
        "ability_bonuses": {"str": 2, "con": 1},
        "speed": 30, "senses": "Darkvision 60 ft.", "languages": "Common, Orc",
        "choice_bonus": 0,
    },
    "Dragonborn": {
        "ability_bonuses": {"str": 2, "cha": 1},
        "speed": 30, "senses": "", "languages": "Common, Draconic",
        "choice_bonus": 0,
    },
    "Tiefling": {
        "ability_bonuses": {"cha": 2, "int": 1},
        "speed": 30, "senses": "Darkvision 60 ft.", "languages": "Common, Infernal",
        "choice_bonus": 0,
    },
}

RACE_NAMES = list(RACES.keys())


def ability_bonus_total(race: str, ability: str, choice_abilities: list[str] | None = None) -> int:
    """The total bonus a given ability gets from this race, including the
    Half-Elf-style 'pick N abilities for +1 each' bonus if applicable."""
    race_data = RACES.get(race)
    if not race_data:
        return 0
    total = race_data["ability_bonuses"].get(ability, 0)
    if ability in (choice_abilities or [])[: race_data.get("choice_bonus", 0)]:
        total += 1
    return total


def apply_bonuses(abilities: dict, race: str, choice_abilities: list[str] | None = None) -> dict:
    """Returns a new abilities dict with this race's bonuses added on top.
    Never mutates the input -- callers keep the raw Standard Array
    assignment separate from the race-adjusted total."""
    return {a: abilities.get(a, 10) + ability_bonus_total(race, a, choice_abilities) for a in ABILITIES}
