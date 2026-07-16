"""SRD monster reference data.

Each entry maps directly to WizardScreen.data keys so it can be passed as
prefill. Fields that the wizard doesn't use (speed, senses, etc.) are stored
here for display purposes in the reference panel but are not written to the DB
through this path -- the CharacterSheetScreen handles them after creation.

Monster data is loaded from data/monsters.json at import time. The fallback
list below is used only if the JSON is missing (development / first-run).
"""
import json as _json
from pathlib import Path as _Path

_DATA_FILE = _Path(__file__).parent / "data" / "monsters.json"

_FALLBACK: list[dict] = [
    # --- CR 0 ---
    {
        "name": "Commoner", "cr": "0", "creature_type": "Humanoid",
        "ac": 10, "hp_max": 4, "speed": "30 ft.",
        "abilities": {"str": 10, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10},
        "saving_throw_proficiencies": [], "skill_proficiencies": {},
        "resistances": "", "immunities": "", "vulnerabilities": "",
        "attacks": [{"name": "Club", "bonus": "+2", "damage": "1d4", "action_cost": "action"}],
        "special_abilities": [], "senses": "passive Perception 10", "languages": "any one",
    },
    # --- CR 1/8 ---
    {
        "name": "Bandit", "cr": "1/8", "creature_type": "Humanoid",
        "ac": 12, "hp_max": 11, "speed": "30 ft.",
        "abilities": {"str": 11, "dex": 12, "con": 12, "int": 10, "wis": 10, "cha": 10},
        "saving_throw_proficiencies": [], "skill_proficiencies": {},
        "resistances": "", "immunities": "", "vulnerabilities": "",
        "attacks": [
            {"name": "Scimitar", "bonus": "+3", "damage": "1d6+1 slashing", "action_cost": "action"},
            {"name": "Shortbow", "bonus": "+3", "damage": "1d6+1 piercing", "action_cost": "action"},
        ],
        "special_abilities": [], "senses": "passive Perception 10", "languages": "any one",
    },
    {
        "name": "Guard", "cr": "1/8", "creature_type": "Humanoid",
        "ac": 16, "hp_max": 11, "speed": "30 ft.",
        "abilities": {"str": 13, "dex": 12, "con": 12, "int": 10, "wis": 11, "cha": 10},
        "saving_throw_proficiencies": [],
        "skill_proficiencies": {"perception": "proficient"},
        "resistances": "", "immunities": "", "vulnerabilities": "",
        "attacks": [{"name": "Spear", "bonus": "+3", "damage": "1d6+1 piercing", "action_cost": "action"}],
        "special_abilities": [], "senses": "passive Perception 13", "languages": "any one",
    },
    {
        "name": "Kobold", "cr": "1/8", "creature_type": "Humanoid",
        "ac": 12, "hp_max": 5, "speed": "30 ft.",
        "abilities": {"str": 7, "dex": 15, "con": 9, "int": 8, "wis": 7, "cha": 8},
        "saving_throw_proficiencies": [], "skill_proficiencies": {},
        "resistances": "", "immunities": "", "vulnerabilities": "",
        "attacks": [
            {"name": "Dagger", "bonus": "+4", "damage": "1d4+2 piercing", "action_cost": "action"},
            {"name": "Sling", "bonus": "+4", "damage": "1d4+2 bludgeoning", "action_cost": "action"},
        ],
        "special_abilities": [
            {"name": "Sunlight Sensitivity", "description": "Disadvantage on attack rolls and Perception checks in sunlight."},
            {"name": "Pack Tactics", "description": "Advantage on attack rolls when an ally is adjacent to target."},
        ],
        "senses": "darkvision 60 ft., passive Perception 8", "languages": "Common, Draconic",
    },
    # --- CR 1/4 ---
    {
        "name": "Goblin", "cr": "1/4", "creature_type": "Humanoid",
        "ac": 15, "hp_max": 7, "speed": "30 ft.",
        "abilities": {"str": 8, "dex": 14, "con": 10, "int": 10, "wis": 8, "cha": 8},
        "saving_throw_proficiencies": [], "skill_proficiencies": {"stealth": "expertise"},
        "resistances": "", "immunities": "", "vulnerabilities": "",
        "attacks": [
            {"name": "Scimitar", "bonus": "+4", "damage": "1d6+2 slashing", "action_cost": "action"},
            {"name": "Shortbow", "bonus": "+4", "damage": "1d6+2 piercing", "action_cost": "action"},
        ],
        "special_abilities": [
            {"name": "Nimble Escape", "description": "Can Disengage or Hide as a bonus action."},
        ],
        "senses": "darkvision 60 ft., passive Perception 9", "languages": "Common, Goblin",
    },
    {
        "name": "Skeleton", "cr": "1/4", "creature_type": "Undead",
        "ac": 13, "hp_max": 13, "speed": "30 ft.",
        "abilities": {"str": 10, "dex": 14, "con": 15, "int": 6, "wis": 8, "cha": 5},
        "saving_throw_proficiencies": [], "skill_proficiencies": {},
        "resistances": "", "immunities": "poison", "vulnerabilities": "bludgeoning",
        "attacks": [
            {"name": "Shortsword", "bonus": "+4", "damage": "1d6+2 piercing", "action_cost": "action"},
            {"name": "Shortbow", "bonus": "+4", "damage": "1d6+2 piercing", "action_cost": "action"},
        ],
        "special_abilities": [], "senses": "darkvision 60 ft., passive Perception 9", "languages": "understands languages it knew in life",
    },
    {
        "name": "Wolf", "cr": "1/4", "creature_type": "Beast",
        "ac": 13, "hp_max": 11, "speed": "40 ft.",
        "abilities": {"str": 12, "dex": 15, "con": 12, "int": 3, "wis": 12, "cha": 6},
        "saving_throw_proficiencies": [],
        "skill_proficiencies": {"perception": "proficient", "stealth": "proficient"},
        "resistances": "", "immunities": "", "vulnerabilities": "",
        "attacks": [{"name": "Bite", "bonus": "+4", "damage": "2d4+2 piercing", "action_cost": "action"}],
        "special_abilities": [
            {"name": "Pack Tactics", "description": "Advantage on attack rolls when an ally is adjacent to target."},
            {"name": "Bite", "description": "DC 11 STR save or knocked prone."},
        ],
        "senses": "passive Perception 13", "languages": "—",
    },
    {
        "name": "Zombie", "cr": "1/4", "creature_type": "Undead",
        "ac": 8, "hp_max": 22, "speed": "20 ft.",
        "abilities": {"str": 13, "dex": 6, "con": 16, "int": 3, "wis": 6, "cha": 5},
        "saving_throw_proficiencies": ["wis"], "skill_proficiencies": {},
        "resistances": "", "immunities": "poison", "vulnerabilities": "",
        "attacks": [{"name": "Slam", "bonus": "+3", "damage": "1d6+1 bludgeoning", "action_cost": "action"}],
        "special_abilities": [
            {"name": "Undead Fortitude", "description": "DC 5 + damage taken CON save to drop to 1 HP instead of 0 (not radiant or crit)."},
        ],
        "senses": "darkvision 60 ft., passive Perception 8", "languages": "understands the languages it knew in life",
    },
    # --- CR 1/2 ---
    {
        "name": "Gnoll", "cr": "1/2", "creature_type": "Humanoid",
        "ac": 15, "hp_max": 22, "speed": "30 ft.",
        "abilities": {"str": 14, "dex": 12, "con": 11, "int": 6, "wis": 10, "cha": 7},
        "saving_throw_proficiencies": [], "skill_proficiencies": {},
        "resistances": "", "immunities": "", "vulnerabilities": "",
        "attacks": [
            {"name": "Bite", "bonus": "+4", "damage": "1d4+2 piercing", "action_cost": "action"},
            {"name": "Spear", "bonus": "+4", "damage": "1d6+2 piercing", "action_cost": "action"},
            {"name": "Longbow", "bonus": "+3", "damage": "1d8+1 piercing", "action_cost": "action"},
        ],
        "special_abilities": [
            {"name": "Rampage", "description": "When it reduces a creature to 0 HP with a melee attack on its turn, can move up to half speed and make a bite attack as a bonus action."},
        ],
        "senses": "darkvision 60 ft., passive Perception 10", "languages": "Gnoll",
    },
    {
        "name": "Hobgoblin", "cr": "1/2", "creature_type": "Humanoid",
        "ac": 18, "hp_max": 11, "speed": "30 ft.",
        "abilities": {"str": 13, "dex": 12, "con": 12, "int": 10, "wis": 10, "cha": 9},
        "saving_throw_proficiencies": [], "skill_proficiencies": {},
        "resistances": "", "immunities": "", "vulnerabilities": "",
        "attacks": [
            {"name": "Longsword", "bonus": "+3", "damage": "1d8+1 slashing", "action_cost": "action"},
            {"name": "Longbow", "bonus": "+3", "damage": "1d8+1 piercing", "action_cost": "action"},
        ],
        "special_abilities": [
            {"name": "Martial Advantage", "description": "Once per turn, can deal extra 2d6 damage if an ally is within 5 ft. of the target."},
        ],
        "senses": "darkvision 60 ft., passive Perception 10", "languages": "Common, Goblin",
    },
    {
        "name": "Orc", "cr": "1/2", "creature_type": "Humanoid",
        "ac": 13, "hp_max": 15, "speed": "30 ft.",
        "abilities": {"str": 16, "dex": 12, "con": 16, "int": 7, "wis": 11, "cha": 10},
        "saving_throw_proficiencies": [],
        "skill_proficiencies": {"intimidation": "proficient"},
        "resistances": "", "immunities": "", "vulnerabilities": "",
        "attacks": [
            {"name": "Greataxe", "bonus": "+5", "damage": "1d12+3 slashing", "action_cost": "action"},
            {"name": "Javelin", "bonus": "+5", "damage": "1d6+3 piercing", "action_cost": "action"},
        ],
        "special_abilities": [
            {"name": "Aggressive", "description": "Bonus action to move up to speed toward a hostile creature."},
        ],
        "senses": "darkvision 60 ft., passive Perception 10", "languages": "Common, Orc",
    },
    # --- CR 1 ---
    {
        "name": "Bugbear", "cr": "1", "creature_type": "Humanoid",
        "ac": 16, "hp_max": 27, "speed": "30 ft.",
        "abilities": {"str": 15, "dex": 14, "con": 13, "int": 8, "wis": 11, "cha": 9},
        "saving_throw_proficiencies": [],
        "skill_proficiencies": {"stealth": "proficient", "survival": "proficient"},
        "resistances": "", "immunities": "", "vulnerabilities": "",
        "attacks": [
            {"name": "Morningstar", "bonus": "+4", "damage": "2d8+2 piercing", "action_cost": "action"},
            {"name": "Javelin", "bonus": "+4", "damage": "2d6+2 piercing", "action_cost": "action"},
        ],
        "special_abilities": [
            {"name": "Brute", "description": "Melee weapon attacks deal one extra die of damage (included)."},
            {"name": "Surprise Attack", "description": "Extra 2d6 damage on first hit if target surprised."},
        ],
        "senses": "darkvision 60 ft., passive Perception 10", "languages": "Common, Goblin",
    },
    {
        "name": "Ghoul", "cr": "1", "creature_type": "Undead",
        "ac": 12, "hp_max": 22, "speed": "30 ft.",
        "abilities": {"str": 13, "dex": 15, "con": 10, "int": 7, "wis": 10, "cha": 6},
        "saving_throw_proficiencies": [], "skill_proficiencies": {},
        "resistances": "", "immunities": "poison", "vulnerabilities": "",
        "attacks": [
            {"name": "Bite", "bonus": "+2", "damage": "2d6+2 piercing", "action_cost": "action"},
            {"name": "Claws", "bonus": "+4", "damage": "2d4+2 slashing", "action_cost": "action"},
        ],
        "special_abilities": [
            {"name": "Claws (Paralysis)", "description": "DC 10 CON save or paralyzed for 1 minute. Not elves or undead."},
        ],
        "senses": "darkvision 60 ft., passive Perception 10", "languages": "Common",
    },
    {
        "name": "Giant Spider", "cr": "1", "creature_type": "Beast",
        "ac": 14, "hp_max": 26, "speed": "30 ft., climb 30 ft.",
        "abilities": {"str": 14, "dex": 16, "con": 12, "int": 2, "wis": 11, "cha": 4},
        "saving_throw_proficiencies": [],
        "skill_proficiencies": {"stealth": "proficient"},
        "resistances": "", "immunities": "", "vulnerabilities": "",
        "attacks": [
            {"name": "Bite", "bonus": "+5", "damage": "1d8+3 piercing + 2d8 poison", "action_cost": "action"},
            {"name": "Web", "bonus": "+5", "damage": "—", "action_cost": "action"},
        ],
        "special_abilities": [
            {"name": "Web (Restrain)", "description": "Ranged attack, DC 12 STR check to escape. Destroys in fire."},
            {"name": "Spider Climb", "description": "Can climb difficult surfaces including ceilings."},
            {"name": "Web Sense", "description": "Knows exact location of any creature touching its web."},
        ],
        "senses": "blindsight 10 ft., darkvision 60 ft., passive Perception 10", "languages": "—",
    },
    {
        "name": "Harpy", "cr": "1", "creature_type": "Monstrosity",
        "ac": 11, "hp_max": 38, "speed": "20 ft., fly 40 ft.",
        "abilities": {"str": 12, "dex": 13, "con": 12, "int": 7, "wis": 10, "cha": 13},
        "saving_throw_proficiencies": [], "skill_proficiencies": {},
        "resistances": "", "immunities": "", "vulnerabilities": "",
        "attacks": [
            {"name": "Claws", "bonus": "+3", "damage": "2d4+1 slashing", "action_cost": "action"},
            {"name": "Club", "bonus": "+3", "damage": "1d4+1 bludgeoning", "action_cost": "action"},
        ],
        "special_abilities": [
            {"name": "Luring Song", "description": "DC 11 WIS save or charmed and incapacitated, moving toward the harpy. Repeats at end of each turn."},
        ],
        "senses": "passive Perception 10", "languages": "Common",
    },
    # --- CR 2 ---
    {
        "name": "Ghast", "cr": "2", "creature_type": "Undead",
        "ac": 13, "hp_max": 36, "speed": "30 ft.",
        "abilities": {"str": 16, "dex": 17, "con": 10, "int": 11, "wis": 10, "cha": 8},
        "saving_throw_proficiencies": [], "skill_proficiencies": {},
        "resistances": "necrotic", "immunities": "poison", "vulnerabilities": "",
        "attacks": [
            {"name": "Bite", "bonus": "+3", "damage": "3d6+3 piercing", "action_cost": "action"},
            {"name": "Claws", "bonus": "+5", "damage": "2d6+3 slashing", "action_cost": "action"},
        ],
        "special_abilities": [
            {"name": "Stench", "description": "DC 10 CON save or poisoned while within 5 ft. New save each turn."},
            {"name": "Claws (Paralysis)", "description": "DC 10 CON save or paralyzed for 1 minute. Not undead or elves."},
            {"name": "Turning Defiance", "description": "Advantage on saves against being turned."},
        ],
        "senses": "darkvision 60 ft., passive Perception 10", "languages": "Common",
    },
    {
        "name": "Gelatinous Cube", "cr": "2", "creature_type": "Ooze",
        "ac": 6, "hp_max": 84, "speed": "15 ft.",
        "abilities": {"str": 14, "dex": 3, "con": 20, "int": 1, "wis": 6, "cha": 1},
        "saving_throw_proficiencies": [], "skill_proficiencies": {},
        "resistances": "", "immunities": "", "vulnerabilities": "",
        "attacks": [{"name": "Pseudopod", "bonus": "+4", "damage": "3d6 acid", "action_cost": "action"}],
        "special_abilities": [
            {"name": "Engulf", "description": "Moves into Large or smaller creature's space. DC 12 DEX save or engulfed (restrained, 6d6 acid at start of turns, can't breathe)."},
            {"name": "Transparent", "description": "DC 15 Perception check to notice cube when it hasn't moved."},
            {"name": "Ooze Cube", "description": "Occupies entire 10-foot cube. Creatures can see through it."},
        ],
        "senses": "blindsight 60 ft. (blind beyond), passive Perception 8", "languages": "—",
    },
    {
        "name": "Ogre", "cr": "2", "creature_type": "Giant",
        "ac": 11, "hp_max": 59, "speed": "40 ft.",
        "abilities": {"str": 19, "dex": 8, "con": 16, "int": 5, "wis": 7, "cha": 7},
        "saving_throw_proficiencies": [], "skill_proficiencies": {},
        "resistances": "", "immunities": "", "vulnerabilities": "",
        "attacks": [
            {"name": "Greatclub", "bonus": "+6", "damage": "2d8+4 bludgeoning", "action_cost": "action"},
            {"name": "Javelin", "bonus": "+6", "damage": "2d6+4 piercing", "action_cost": "action"},
        ],
        "special_abilities": [], "senses": "darkvision 60 ft., passive Perception 8", "languages": "Common, Giant",
    },
    {
        "name": "Wererat", "cr": "2", "creature_type": "Humanoid (shapechanger)",
        "ac": 12, "hp_max": 33, "speed": "30 ft.",
        "abilities": {"str": 10, "dex": 15, "con": 12, "int": 11, "wis": 10, "cha": 8},
        "saving_throw_proficiencies": [], "skill_proficiencies": {"perception": "proficient", "stealth": "proficient"},
        "resistances": "", "immunities": "bludgeoning, piercing, and slashing from nonmagical weapons that aren't silvered", "vulnerabilities": "",
        "attacks": [
            {"name": "Shortsword", "bonus": "+4", "damage": "1d6+2 piercing", "action_cost": "action"},
            {"name": "Hand Crossbow", "bonus": "+4", "damage": "1d6+2 piercing", "action_cost": "action"},
            {"name": "Bite (rat form)", "bonus": "+4", "damage": "1d4+2 piercing", "action_cost": "action"},
        ],
        "special_abilities": [
            {"name": "Shapechanger", "description": "Can polymorph into rat-humanoid hybrid or giant rat, or back to humanoid."},
            {"name": "Bite Curse", "description": "Humanoid bitten must succeed DC 11 CON save or be cursed with lycanthropy."},
        ],
        "senses": "darkvision 60 ft., passive Perception 13", "languages": "Common",
    },
    # --- CR 3 ---
    {
        "name": "Manticore", "cr": "3", "creature_type": "Monstrosity",
        "ac": 14, "hp_max": 68, "speed": "30 ft., fly 50 ft.",
        "abilities": {"str": 17, "dex": 16, "con": 17, "int": 7, "wis": 12, "cha": 8},
        "saving_throw_proficiencies": [], "skill_proficiencies": {},
        "resistances": "", "immunities": "", "vulnerabilities": "",
        "attacks": [
            {"name": "Bite", "bonus": "+5", "damage": "1d8+3 piercing", "action_cost": "action"},
            {"name": "Claw", "bonus": "+5", "damage": "2d6+3 slashing", "action_cost": "action"},
            {"name": "Tail Spike", "bonus": "+5", "damage": "2d8+3 piercing", "action_cost": "action"},
        ],
        "special_abilities": [
            {"name": "Tail Spikes (4/day)", "description": "Fires up to 3 tail spikes as one ranged attack action. Range 100/200 ft."},
        ],
        "senses": "darkvision 60 ft., passive Perception 11", "languages": "Common",
    },
    {
        "name": "Owlbear", "cr": "3", "creature_type": "Monstrosity",
        "ac": 13, "hp_max": 59, "speed": "40 ft.",
        "abilities": {"str": 20, "dex": 12, "con": 17, "int": 3, "wis": 12, "cha": 7},
        "saving_throw_proficiencies": [],
        "skill_proficiencies": {"perception": "proficient"},
        "resistances": "", "immunities": "", "vulnerabilities": "",
        "attacks": [
            {"name": "Beak", "bonus": "+7", "damage": "1d10+5 piercing", "action_cost": "action"},
            {"name": "Claws", "bonus": "+7", "damage": "2d8+5 slashing", "action_cost": "action"},
        ],
        "special_abilities": [
            {"name": "Keen Sight and Smell", "description": "Advantage on Perception checks relying on sight or smell."},
        ],
        "senses": "darkvision 60 ft., passive Perception 13", "languages": "—",
    },
    {
        "name": "Veteran", "cr": "3", "creature_type": "Humanoid",
        "ac": 17, "hp_max": 58, "speed": "30 ft.",
        "abilities": {"str": 16, "dex": 13, "con": 14, "int": 10, "wis": 11, "cha": 10},
        "saving_throw_proficiencies": [],
        "skill_proficiencies": {"athletics": "proficient", "perception": "proficient"},
        "resistances": "", "immunities": "", "vulnerabilities": "",
        "attacks": [
            {"name": "Longsword", "bonus": "+5", "damage": "1d8+3 slashing", "action_cost": "action"},
            {"name": "Shortsword", "bonus": "+5", "damage": "1d6+3 piercing", "action_cost": "bonus action"},
            {"name": "Heavy Crossbow", "bonus": "+3", "damage": "1d10+1 piercing", "action_cost": "action"},
        ],
        "special_abilities": [
            {"name": "Multiattack", "description": "Makes two longsword attacks. Can replace one with shortsword."},
        ],
        "senses": "passive Perception 12", "languages": "any one",
    },
    {
        "name": "Wight", "cr": "3", "creature_type": "Undead",
        "ac": 14, "hp_max": 45, "speed": "30 ft.",
        "abilities": {"str": 15, "dex": 14, "con": 16, "int": 10, "wis": 13, "cha": 15},
        "saving_throw_proficiencies": [],
        "skill_proficiencies": {"perception": "proficient", "stealth": "proficient"},
        "resistances": "necrotic; bludgeoning, piercing, slashing (nonmagical non-silver)", "immunities": "poison", "vulnerabilities": "",
        "attacks": [
            {"name": "Longsword", "bonus": "+4", "damage": "1d8+2 slashing", "action_cost": "action"},
            {"name": "Longbow", "bonus": "+4", "damage": "1d8+2 piercing", "action_cost": "action"},
            {"name": "Life Drain", "bonus": "+4", "damage": "3d6 necrotic", "action_cost": "action"},
        ],
        "special_abilities": [
            {"name": "Life Drain", "description": "DC 13 CON save or max HP reduced by damage dealt. Target dies if max HP 0. Undead and constructs immune."},
            {"name": "Create Specter", "description": "Can create specter from humanoid slain by Life Drain."},
            {"name": "Sunlight Sensitivity", "description": "Disadvantage on attacks and Perception checks in sunlight."},
        ],
        "senses": "darkvision 60 ft., passive Perception 13", "languages": "the languages it knew in life",
    },
    # --- CR 4 ---
    {
        "name": "Banshee", "cr": "4", "creature_type": "Undead",
        "ac": 12, "hp_max": 58, "speed": "0 ft., fly 40 ft. (hover)",
        "abilities": {"str": 1, "dex": 14, "con": 10, "int": 12, "wis": 11, "cha": 17},
        "saving_throw_proficiencies": ["wis", "cha"],
        "skill_proficiencies": {},
        "resistances": "acid, fire, lightning, thunder; bludgeoning, piercing, slashing (nonmagical)", "immunities": "cold, necrotic, poison", "vulnerabilities": "",
        "attacks": [
            {"name": "Corrupting Touch", "bonus": "+4", "damage": "3d6+2 necrotic", "action_cost": "action"},
        ],
        "special_abilities": [
            {"name": "Horrifying Visage", "description": "DC 13 WIS save or frightened for 1 minute. Repeats at end of each turn."},
            {"name": "Wail (1/day)", "description": "DC 13 CON save or drop to 0 HP. Immune if can't hear. 30 ft. range."},
            {"name": "Detect Life", "description": "Magically senses living creatures within 5 miles."},
        ],
        "senses": "darkvision 60 ft., passive Perception 10", "languages": "Common (can't speak)",
    },
    {
        "name": "Ettin", "cr": "4", "creature_type": "Giant",
        "ac": 12, "hp_max": 85, "speed": "40 ft.",
        "abilities": {"str": 21, "dex": 8, "con": 17, "int": 6, "wis": 10, "cha": 8},
        "saving_throw_proficiencies": [],
        "skill_proficiencies": {"perception": "proficient"},
        "resistances": "", "immunities": "", "vulnerabilities": "",
        "attacks": [
            {"name": "Battleaxe", "bonus": "+7", "damage": "2d8+5 slashing", "action_cost": "action"},
            {"name": "Morningstar", "bonus": "+7", "damage": "2d8+5 piercing", "action_cost": "action"},
        ],
        "special_abilities": [
            {"name": "Two Heads", "description": "Advantage on Perception and saves against being blinded, charmed, deafened, frightened, stunned, or knocked unconscious."},
            {"name": "Multiattack", "description": "Makes two attacks: one with each weapon."},
            {"name": "Wakeful", "description": "One head sleeps while the other is awake. Can't be surprised."},
        ],
        "senses": "darkvision 60 ft., passive Perception 14", "languages": "Giant, Orc",
    },
    # --- CR 5 ---
    {
        "name": "Hill Giant", "cr": "5", "creature_type": "Giant",
        "ac": 13, "hp_max": 105, "speed": "40 ft.",
        "abilities": {"str": 21, "dex": 8, "con": 19, "int": 5, "wis": 9, "cha": 6},
        "saving_throw_proficiencies": [],
        "skill_proficiencies": {"perception": "proficient"},
        "resistances": "", "immunities": "", "vulnerabilities": "",
        "attacks": [
            {"name": "Greatclub", "bonus": "+8", "damage": "3d8+5 bludgeoning", "action_cost": "action"},
            {"name": "Rock", "bonus": "+8", "damage": "3d10+5 bludgeoning", "action_cost": "action"},
        ],
        "special_abilities": [
            {"name": "Multiattack", "description": "Makes two greatclub attacks."},
        ],
        "senses": "passive Perception 12", "languages": "Giant",
    },
    {
        "name": "Troll", "cr": "5", "creature_type": "Giant",
        "ac": 15, "hp_max": 84, "speed": "30 ft.",
        "abilities": {"str": 18, "dex": 13, "con": 20, "int": 7, "wis": 9, "cha": 7},
        "saving_throw_proficiencies": [],
        "skill_proficiencies": {"perception": "proficient"},
        "resistances": "", "immunities": "", "vulnerabilities": "",
        "attacks": [
            {"name": "Bite", "bonus": "+7", "damage": "1d6+4 piercing", "action_cost": "action"},
            {"name": "Claw", "bonus": "+7", "damage": "2d6+4 slashing", "action_cost": "action"},
        ],
        "special_abilities": [
            {"name": "Regeneration", "description": "Regains 10 HP at start of turn. Doesn't regenerate if it took acid or fire damage this turn."},
            {"name": "Multiattack", "description": "Makes three attacks: one bite and two claws."},
            {"name": "Keen Smell", "description": "Advantage on Perception checks that rely on smell."},
        ],
        "senses": "darkvision 60 ft., passive Perception 13", "languages": "Giant",
    },
    {
        "name": "Vampire Spawn", "cr": "5", "creature_type": "Undead",
        "ac": 15, "hp_max": 82, "speed": "30 ft., climb 30 ft.",
        "abilities": {"str": 16, "dex": 16, "con": 16, "int": 11, "wis": 10, "cha": 12},
        "saving_throw_proficiencies": ["dex", "wis"],
        "skill_proficiencies": {"perception": "proficient", "stealth": "proficient"},
        "resistances": "necrotic; bludgeoning, piercing, slashing (nonmagical)", "immunities": "", "vulnerabilities": "",
        "attacks": [
            {"name": "Claws", "bonus": "+6", "damage": "2d4+3 slashing", "action_cost": "action"},
            {"name": "Bite", "bonus": "+6", "damage": "1d6+3 piercing + 3d6 necrotic", "action_cost": "action"},
        ],
        "special_abilities": [
            {"name": "Bite (Life Drain)", "description": "Target's max HP reduced by necrotic damage. Vampire regains HP equal to reduction."},
            {"name": "Spider Climb", "description": "Can climb difficult surfaces including ceilings."},
            {"name": "Sunlight Hypersensitivity", "description": "Takes 20 radiant damage in sunlight. Disadvantage on attacks and checks in sunlight."},
        ],
        "senses": "darkvision 60 ft., passive Perception 13", "languages": "the languages it knew in life",
    },
    # --- CR 6 ---
    {
        "name": "Mummy", "cr": "6", "creature_type": "Undead",
        "ac": 11, "hp_max": 58, "speed": "20 ft.",
        "abilities": {"str": 16, "dex": 8, "con": 15, "int": 6, "wis": 10, "cha": 12},
        "saving_throw_proficiencies": ["wis"],
        "skill_proficiencies": {},
        "resistances": "bludgeoning, piercing, slashing (nonmagical)", "immunities": "necrotic, poison", "vulnerabilities": "fire",
        "attacks": [
            {"name": "Multiattack", "bonus": "—", "damage": "—", "action_cost": "action"},
            {"name": "Rotting Fist", "bonus": "+5", "damage": "2d6+3 bludgeoning + 3d6 necrotic", "action_cost": "action"},
        ],
        "special_abilities": [
            {"name": "Rotting Fist (Curse)", "description": "DC 12 CON save or cursed with mummy rot: can't regain HP, max HP decreases by 3d6 each 24 hours. Dies if max HP reaches 0. Cured by remove curse."},
            {"name": "Dreadful Glare", "description": "DC 11 WIS save or frightened until end of next turn. On fail by 5+, also paralyzed."},
        ],
        "senses": "darkvision 60 ft., passive Perception 10", "languages": "the languages it knew in life",
    },
    {
        "name": "Wyvern", "cr": "6", "creature_type": "Dragon",
        "ac": 13, "hp_max": 110, "speed": "20 ft., fly 80 ft.",
        "abilities": {"str": 19, "dex": 10, "con": 16, "int": 5, "wis": 12, "cha": 6},
        "saving_throw_proficiencies": [],
        "skill_proficiencies": {"perception": "proficient"},
        "resistances": "", "immunities": "", "vulnerabilities": "",
        "attacks": [
            {"name": "Bite", "bonus": "+7", "damage": "2d6+4 piercing", "action_cost": "action"},
            {"name": "Claws", "bonus": "+7", "damage": "2d8+4 slashing", "action_cost": "action"},
            {"name": "Stinger", "bonus": "+7", "damage": "2d6+4 piercing + 7d6 poison", "action_cost": "action"},
        ],
        "special_abilities": [
            {"name": "Multiattack", "description": "Makes two attacks: bite and stinger, or claws and stinger."},
            {"name": "Stinger Poison", "description": "DC 15 CON save or take full poison damage (half on success)."},
        ],
        "senses": "darkvision 60 ft., passive Perception 14", "languages": "—",
    },
    # --- CR 8 ---
    {
        "name": "Young Red Dragon", "cr": "8", "creature_type": "Dragon",
        "ac": 18, "hp_max": 178, "speed": "40 ft., climb 40 ft., fly 80 ft.",
        "abilities": {"str": 23, "dex": 10, "con": 21, "int": 14, "wis": 11, "cha": 19},
        "saving_throw_proficiencies": ["dex", "con", "wis", "cha"],
        "skill_proficiencies": {"perception": "proficient", "stealth": "proficient"},
        "resistances": "", "immunities": "fire", "vulnerabilities": "",
        "attacks": [
            {"name": "Bite", "bonus": "+10", "damage": "2d10+6 piercing + 1d6 fire", "action_cost": "action"},
            {"name": "Claw", "bonus": "+10", "damage": "2d6+6 slashing", "action_cost": "action"},
            {"name": "Fire Breath (Recharge 5-6)", "bonus": "—", "damage": "16d6 fire", "action_cost": "action"},
        ],
        "special_abilities": [
            {"name": "Multiattack", "description": "Makes three attacks: one bite and two claws."},
            {"name": "Fire Breath (30 ft. cone)", "description": "DC 17 DEX save. 16d6 fire on fail, half on success."},
        ],
        "senses": "blindsight 30 ft., darkvision 120 ft., passive Perception 18", "languages": "Common, Draconic",
    },
    # --- CR 10 ---
    {
        "name": "Young Blue Dragon", "cr": "10", "creature_type": "Dragon",
        "ac": 18, "hp_max": 152, "speed": "40 ft., burrow 20 ft., fly 80 ft.",
        "abilities": {"str": 21, "dex": 10, "con": 19, "int": 14, "wis": 13, "cha": 17},
        "saving_throw_proficiencies": ["dex", "con", "wis", "cha"],
        "skill_proficiencies": {"perception": "proficient", "stealth": "proficient"},
        "resistances": "", "immunities": "lightning", "vulnerabilities": "",
        "attacks": [
            {"name": "Bite", "bonus": "+9", "damage": "2d10+5 piercing + 1d10 lightning", "action_cost": "action"},
            {"name": "Claw", "bonus": "+9", "damage": "2d6+5 slashing", "action_cost": "action"},
            {"name": "Lightning Breath (Recharge 5-6)", "bonus": "—", "damage": "8d10 lightning", "action_cost": "action"},
        ],
        "special_abilities": [
            {"name": "Multiattack", "description": "Makes three attacks: one bite and two claws."},
            {"name": "Lightning Breath (90 ft. line)", "description": "DC 16 DEX save. 8d10 lightning on fail, half on success."},
        ],
        "senses": "blindsight 30 ft., darkvision 120 ft., passive Perception 19", "languages": "Common, Draconic",
    },
    # --- CR 13 ---
    {
        "name": "Vampire", "cr": "13", "creature_type": "Undead (shapechanger)",
        "ac": 16, "hp_max": 144, "speed": "30 ft., climb 30 ft.",
        "abilities": {"str": 18, "dex": 18, "con": 18, "int": 17, "wis": 15, "cha": 18},
        "saving_throw_proficiencies": ["dex", "wis", "cha"],
        "skill_proficiencies": {"perception": "proficient", "stealth": "proficient"},
        "resistances": "necrotic; bludgeoning, piercing, slashing (nonmagical)", "immunities": "", "vulnerabilities": "",
        "attacks": [
            {"name": "Unarmed Strike", "bonus": "+9", "damage": "1d8+4 bludgeoning", "action_cost": "action"},
            {"name": "Bite", "bonus": "+9", "damage": "1d6+4 piercing + 3d6 necrotic", "action_cost": "action"},
        ],
        "special_abilities": [
            {"name": "Bite (Life Drain)", "description": "Target's max HP reduced by necrotic damage. Vampire regains HP equal to reduction."},
            {"name": "Shapechanger", "description": "Can polymorph into Tiny bat or Medium cloud of mist."},
            {"name": "Legendary Resistance (3/day)", "description": "Can choose to succeed on a failed saving throw."},
            {"name": "Misty Escape", "description": "When reduced to 0 HP outside lair, transforms to mist if not in sunlight or running water."},
            {"name": "Sunlight Hypersensitivity", "description": "Takes 20 radiant damage in sunlight. Disadvantage on attacks and checks."},
        ],
        "senses": "darkvision 120 ft., passive Perception 17", "languages": "the languages it knew in life",
    },
    # --- CR 21 ---
    {
        "name": "Lich", "cr": "21", "creature_type": "Undead",
        "ac": 17, "hp_max": 135, "speed": "30 ft.",
        "abilities": {"str": 11, "dex": 16, "con": 16, "int": 20, "wis": 14, "cha": 16},
        "saving_throw_proficiencies": ["con", "int", "wis"],
        "skill_proficiencies": {"arcana": "expertise", "history": "proficient", "insight": "proficient", "perception": "proficient"},
        "resistances": "cold, lightning, necrotic", "immunities": "poison; charmed, exhaustion, frightened, paralyzed, poisoned", "vulnerabilities": "",
        "attacks": [
            {"name": "Paralyzing Touch", "bonus": "+12", "damage": "3d6 cold", "action_cost": "action"},
        ],
        "special_abilities": [
            {"name": "Paralyzing Touch", "description": "DC 18 CON save or paralyzed for 1 minute. Repeat save at end of each turn."},
            {"name": "Legendary Resistance (3/day)", "description": "Can choose to succeed on a failed saving throw."},
            {"name": "Rejuvenation", "description": "If destroyed and phylactery intact, returns in 1d10 days with all HP."},
            {"name": "Spellcasting (INT, DC 20, +12 to hit)", "description": "Cantrips: mage hand, prestidigitation, ray of frost. 1st (4 slots): detect magic, magic missile, shield, thunderwave. 2nd (3): acid arrow, detect thoughts, invisibility, mirror image. 3rd (3): animate dead, counterspell, dispel magic, fireball. 4th (3): blight, dimension door. 5th (3): cloudkill, scrying. 6th (1): disintegrate, globe of invulnerability. 7th (1): finger of death, plane shift. 8th (1): dominate monster, power word stun. 9th (1): power word kill."},
            {"name": "Turn Resistance", "description": "Advantage on saves against being turned."},
        ],
        "senses": "truesight 120 ft., passive Perception 20", "languages": "Common plus five others",
    },
]

try:
    MONSTERS: list[dict] = _json.loads(_DATA_FILE.read_text(encoding="utf-8"))
except (FileNotFoundError, _json.JSONDecodeError):
    MONSTERS = _FALLBACK


def search(query: str) -> list[dict]:
    """Return monsters whose name or CR contains the query (case-insensitive)."""
    q = query.strip().lower()
    if not q:
        return MONSTERS
    return [m for m in MONSTERS if q in m["name"].lower() or q == m["cr"].lower()]


def find(name: str) -> dict | None:
    """Return first monster matching name exactly (case-insensitive), or None."""
    name_l = name.strip().lower()
    return next((m for m in MONSTERS if m["name"].lower() == name_l), None)


def wizard_prefill(monster: dict) -> dict:
    """Build a WizardScreen-compatible prefill dict from a monster entry."""
    return {
        "name": monster["name"],
        "cr": monster["cr"],
        "creature_type": monster["creature_type"],
        "ac": monster["ac"],
        "hp_max": monster["hp_max"],
        "abilities": dict(monster["abilities"]),
        "saving_throw_proficiencies": list(monster.get("saving_throw_proficiencies", [])),
        "skill_proficiencies": dict(monster.get("skill_proficiencies", {})),
        "resistances": monster.get("resistances", ""),
        "immunities": monster.get("immunities", ""),
        "vulnerabilities": monster.get("vulnerabilities", ""),
        "attacks": [dict(a) for a in monster.get("attacks", [])],
        "special_abilities": [dict(s) for s in monster.get("special_abilities", [])],
    }
