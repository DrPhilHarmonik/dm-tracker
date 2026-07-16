from dataclasses import dataclass, field


ENTITY_TYPES = ["npc", "adventurer", "enemy", "location", "quest", "faction", "item", "session", "encounter"]

ENTITY_LABELS = {
    "npc": "NPC",
    "adventurer": "Adventurer",
    "enemy": "Enemy",
    "location": "Location",
    "quest": "Quest",
    "faction": "Faction",
    "item": "Item",
    "session": "Session",
    "encounter": "Encounter",
}

ENTITY_LABELS_PLURAL = {
    "npc": "NPCs",
    "adventurer": "Adventurers",
    "enemy": "Enemies",
    "location": "Locations",
    "quest": "Quests",
    "faction": "Factions",
    "item": "Items",
    "session": "Sessions",
    "encounter": "Encounters",
}

ENTITY_ICONS = {
    "npc": "person",
    "adventurer": "shield",
    "enemy": "skull",
    "location": "map-pin",
    "quest": "scroll",
    "faction": "users",
    "item": "gem",
    "session": "calendar",
    "encounter": "swords",
}

# Each schema entry: (field_key, label, type, choices_or_None)
# type: "text" | "select" | "number"
ENTITY_SCHEMAS: dict[str, list[tuple]] = {
    "npc": [
        ("race", "Race", "text", None),
        ("role", "Role / Title", "text", None),
        ("alignment", "Alignment", "select", [
            "Lawful Good", "Neutral Good", "Chaotic Good",
            "Lawful Neutral", "True Neutral", "Chaotic Neutral",
            "Lawful Evil", "Neutral Evil", "Chaotic Evil", "Unknown",
        ]),
        ("status", "Status", "select", ["Alive", "Dead", "Missing", "Unknown"]),
        ("location", "Current Location", "entity_ref", "location"),
    ],
    "adventurer": [
        ("race", "Race", "text", None),
        ("class_name", "Class", "text", None),
        ("level", "Level", "number", None),
        ("player_name", "Player Name", "text", None),
        ("alignment", "Alignment", "select", [
            "Lawful Good", "Neutral Good", "Chaotic Good",
            "Lawful Neutral", "True Neutral", "Chaotic Neutral",
            "Lawful Evil", "Neutral Evil", "Chaotic Evil", "Unknown",
        ]),
        ("status", "Status", "select", ["Active", "Retired", "Dead", "Missing"]),
        ("xp", "XP", "number", None),
        ("inspiration", "Inspiration", "boolean", None),
    ],
    "enemy": [
        ("creature_type", "Creature Type", "text", None),
        ("cr", "Challenge Rating", "text", None),
        ("alignment", "Alignment", "select", [
            "Lawful Good", "Neutral Good", "Chaotic Good",
            "Lawful Neutral", "True Neutral", "Chaotic Neutral",
            "Lawful Evil", "Neutral Evil", "Chaotic Evil", "Unaligned",
        ]),
        ("status", "Status", "select", ["Alive", "Defeated", "Fled", "Unknown"]),
    ],
    "location": [
        ("location_type", "Type", "select", [
            "City", "Town", "Village", "Dungeon", "Wilderness", "Ruin",
            "Inn / Tavern", "Temple", "Keep / Fortress", "Plane", "Other",
        ]),
        ("region", "Region", "text", None),
        ("danger_level", "Danger Level", "select", [
            "Safe", "Low", "Moderate", "High", "Deadly", "Unknown",
        ]),
        ("population", "Population", "text", None),
    ],
    "quest": [
        ("status", "Status", "select", ["Active", "Complete", "Failed", "On Hold", "Rumor"]),
        ("difficulty", "Difficulty", "select", ["Trivial", "Easy", "Medium", "Hard", "Deadly"]),
        ("giver", "Quest Giver", "text", None),
        ("reward", "Reward", "text", None),
        ("deadline", "Deadline", "text", None),
    ],
    "faction": [
        ("faction_type", "Type", "select", [
            "Guild", "Government", "Religion", "Criminal", "Military",
            "Arcane Order", "Adventurers Guild", "Cult", "Other",
        ]),
        ("alignment", "Alignment", "select", [
            "Lawful Good", "Neutral Good", "Chaotic Good",
            "Lawful Neutral", "True Neutral", "Chaotic Neutral",
            "Lawful Evil", "Neutral Evil", "Chaotic Evil", "Unknown",
        ]),
        ("power_level", "Power Level", "select", ["Weak", "Minor", "Moderate", "Major", "Dominant"]),
        ("leader", "Leader", "text", None),
        ("headquarters", "Headquarters", "text", None),
    ],
    "item": [
        ("item_type", "Type", "select", [
            "Weapon", "Armor", "Shield", "Wand / Staff", "Ring", "Potion",
            "Scroll", "Artifact", "Trinket", "Vehicle", "Other",
        ]),
        ("rarity", "Rarity", "select", [
            "Common", "Uncommon", "Rare", "Very Rare", "Legendary", "Artifact",
        ]),
        ("attunement", "Attunement", "select", ["Required", "Not Required", "Unknown"]),
        ("owner", "Current Owner", "text", None),
        ("value", "Value / Price", "text", None),
    ],
    "session": [
        ("session_number", "Session #", "number", None),
        ("session_date", "Real Date (YYYY-MM-DD)", "text", None),
        ("in_game_date", "In-Game Date", "text", None),
        ("location", "Primary Location", "entity_ref", "location"),
    ],
    "encounter": [
        ("status", "Status", "select", ["Planned", "Active", "Complete"]),
        ("location", "Location", "entity_ref", "location"),
    ],
}

# Valid relationship type strings
RELATIONSHIP_TYPES = [
    "lives in",
    "located at",
    "belongs to",
    "leads",
    "member of",
    "allies with",
    "opposes",
    "involves",
    "owns",
    "gave quest",
    "completed quest",
    "occurred at",
    "participated in",
    "knows",
    "employs",
    "seeks",
    "guards",
    "worships",
    "created",
    "related to",
    "hostile form of",
    "allied form of",
    "summoned by",
]
