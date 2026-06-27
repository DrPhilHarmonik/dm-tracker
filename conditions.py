"""SRD condition library: names + mechanical summaries for the DM reference panel."""

CONDITIONS: dict[str, str] = {
    "Blinded": (
        "Can't see; auto-fails sight-based checks. "
        "Attack rolls against have advantage; its attack rolls have disadvantage."
    ),
    "Charmed": (
        "Can't attack the charmer or target them with harmful abilities. "
        "Charmer has advantage on social checks against this creature."
    ),
    "Deafened": "Can't hear; auto-fails hearing-based ability checks.",
    "Exhaustion": (
        "Cumulative levels: 1=disadv. ability checks; 2=halved speed; "
        "3=disadv. attacks & saves; 4=halved HP max; 5=speed 0; 6=death."
    ),
    "Frightened": (
        "Disadv. on ability checks and attacks while source of fear is in line of sight. "
        "Can't willingly move closer to source."
    ),
    "Grappled": "Speed 0. Ends if grappler is Incapacitated or creature is moved out of grappler's reach.",
    "Incapacitated": "Can't take actions or reactions.",
    "Invisible": (
        "Can't be seen without special sense. "
        "Attacks against have disadvantage; its attacks have advantage."
    ),
    "Paralyzed": (
        "Incapacitated; can't move or speak. Auto-fails STR and DEX saves. "
        "Attacks against have advantage; hits within 5 ft. are critical."
    ),
    "Petrified": (
        "Incapacitated, can't move or speak, unaware of surroundings. "
        "Auto-fails STR/DEX saves. Resistance to all damage; immune to poison and disease."
    ),
    "Poisoned": "Disadvantage on attack rolls and ability checks.",
    "Prone": (
        "Must crawl (half speed) or stand up (half speed). "
        "Disadv. on attacks. Melee attacks against have advantage; ranged attacks have disadvantage."
    ),
    "Restrained": (
        "Speed 0. Attack rolls have disadvantage; attacks against have advantage. "
        "DEX saves at disadvantage."
    ),
    "Stunned": (
        "Incapacitated; can't move; can speak only falteringly. "
        "Auto-fails STR and DEX saves. Attacks against have advantage."
    ),
    "Unconscious": (
        "Incapacitated, can't move or speak, unaware of surroundings; drops held items, falls prone. "
        "Auto-fails STR/DEX saves; attacks against have advantage; hits within 5 ft. are critical."
    ),
}

CONDITION_NAMES: list[str] = list(CONDITIONS.keys())
