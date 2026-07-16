"""One-time script to fetch all SRD monsters from open5e and write data/monsters.json.

Usage: python dev/build_srd.py
Output: data/monsters.json (committed to the repo)
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

BASE = "https://api.open5e.com/v1/monsters/?document__slug=wotc-srd&limit=100"
OUT = Path(__file__).parent.parent / "data" / "monsters.json"

SAVE_MAP = {
    "strength_save": "str",
    "dexterity_save": "dex",
    "constitution_save": "con",
    "intelligence_save": "int",
    "wisdom_save": "wis",
    "charisma_save": "cha",
}


def fetch_all() -> list[dict]:
    monsters = []
    url = BASE
    while url:
        print(f"  fetching {url}", file=sys.stderr)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 dm-tracker/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
        monsters.extend(data["results"])
        url = data.get("next")
    return monsters


def fmt_speed(speed: dict) -> str:
    if not speed or not isinstance(speed, dict):
        return "30 ft."
    parts = []
    if "walk" in speed:
        parts.append(f"{speed['walk']} ft.")
    for key in ("burrow", "climb", "fly", "hover", "swim"):
        if key in speed and speed[key]:
            # hover is a flag in some entries
            if key == "hover":
                parts[-1] += " (hover)" if parts else "hover"
            else:
                parts.append(f"{key} {speed[key]} ft.")
    return ", ".join(parts) or "30 ft."


def extract_damage_type(desc: str) -> str:
    """Pull damage type word(s) from a Hit: ... sentence."""
    m = re.search(
        r"Hit:.*?\d+\s*\(.*?\)\s+([\w ,/]+?)\s+damage",
        desc,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    m = re.search(r"Hit:.*?\+\d+\s+([\w ,/]+?)\s+damage", desc, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return ""


def convert_action(action: dict) -> dict:
    """Convert an open5e action to our attacks schema."""
    name = action["name"]
    desc = action.get("desc", "")
    bonus_raw = action.get("attack_bonus")
    dice = action.get("damage_dice", "")
    db = action.get("damage_bonus", 0)

    if bonus_raw is not None:
        bonus = f"+{bonus_raw}"
        damage_type = extract_damage_type(desc)
        if dice:
            dmg = f"{dice}+{db} {damage_type}".strip() if db else f"{dice} {damage_type}".strip()
        else:
            dmg = damage_type or "—"
    else:
        bonus = "—"
        dmg = "—"

    return {
        "name": name,
        "bonus": bonus,
        "damage": dmg,
        "action_cost": "action",
    }


def convert_monster(m: dict) -> dict:
    # CR: prefer the string form (e.g. "1/8", "1/4", "1/2")
    cr = str(m.get("challenge_rating") or m.get("cr", "0"))
    # open5e sometimes gives "0.5" for "1/2" etc -- normalise
    float_to_frac = {"0.125": "1/8", "0.25": "1/4", "0.5": "1/2"}
    cr = float_to_frac.get(cr, cr)
    # strip trailing ".0"
    if cr.endswith(".0"):
        cr = cr[:-2]

    # creature type
    subtype = m.get("subtype", "").strip()
    type_ = m.get("type", "Unknown")
    creature_type = f"{type_} ({subtype})" if subtype else type_

    # abilities
    abilities = {
        "str": m.get("strength", 10),
        "dex": m.get("dexterity", 10),
        "con": m.get("constitution", 10),
        "int": m.get("intelligence", 10),
        "wis": m.get("wisdom", 10),
        "cha": m.get("charisma", 10),
    }

    # saving throw proficiencies: include any that are not null
    save_profs = [
        abbr for field, abbr in SAVE_MAP.items() if m.get(field) is not None
    ]

    # skill proficiencies: map everything to "proficient"
    skill_profs = {k: "proficient" for k in (m.get("skills") or {}).keys()}

    # attacks: actions that are actual attack rolls ("to hit" in desc)
    # everything else (breath weapons, multiattack, saves) -> special_abilities
    actions = m.get("actions") or []
    attacks = [
        convert_action(a) for a in actions
        if a.get("attack_bonus") is not None
        and "to hit" in a.get("desc", "").lower()
    ]
    non_attack_actions = [
        {"name": a["name"], "description": a.get("desc", "")}
        for a in actions
        if not (a.get("attack_bonus") is not None and "to hit" in a.get("desc", "").lower())
    ]

    # special_abilities from the dedicated field
    srd_specials = [
        {"name": s["name"], "description": s.get("desc", "")}
        for s in (m.get("special_abilities") or [])
    ]

    special_abilities = srd_specials + non_attack_actions

    return {
        "name": m["name"],
        "cr": cr,
        "creature_type": creature_type,
        "ac": m.get("armor_class", 10),
        "hp_max": m.get("hit_points", 1),
        "speed": fmt_speed(m.get("speed")),
        "abilities": abilities,
        "saving_throw_proficiencies": save_profs,
        "skill_proficiencies": skill_profs,
        "resistances": m.get("damage_resistances", ""),
        "immunities": m.get("damage_immunities", ""),
        "vulnerabilities": m.get("damage_vulnerabilities", ""),
        "attacks": attacks,
        "special_abilities": special_abilities,
        "senses": m.get("senses", ""),
        "languages": m.get("languages", "—"),
    }


def main():
    print("Fetching SRD monsters from open5e...", file=sys.stderr)
    raw = fetch_all()
    print(f"  {len(raw)} monsters fetched", file=sys.stderr)

    converted = [convert_monster(m) for m in raw]

    # Sort by numeric CR then name
    def cr_sort_key(m):
        cr = m["cr"]
        frac = {"1/8": 0.125, "1/4": 0.25, "1/2": 0.5}
        try:
            return (frac.get(cr, float(cr)), m["name"])
        except ValueError:
            return (0.0, m["name"])

    converted.sort(key=cr_sort_key)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(converted, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(converted)} monsters to {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
