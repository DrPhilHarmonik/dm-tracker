"""D&D Beyond encounter JSON importer.

Targets the D&D Beyond Encounter Builder export format (ddb.ac/encounters >
Export). The export lists monster names and quantities; stat blocks are resolved
against the local SRD monster database (data/monsters.json).

Monsters not found in the SRD are still created as enemies with minimal stats
and a note flagging them for manual completion.

The "monsters" key may also appear as "creatures" across DDB export versions;
per-monster count is accepted as "quantity", "count", or "number".
"""
import json
from pathlib import Path

import db
import srd
import sheet as shm


def parse_ddb_encounter(path: str | Path) -> dict:
    """Parse a D&D Beyond encounter export JSON.

    Returns:
        {
            "encounter_name": str,
            "monsters": [{"name": str, "count": int, "srd_monster": dict | None}]
        }

    Raises ValueError on format mismatch or if no monsters are found.
    """
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"Could not read JSON: {e}") from e

    encounter_name = str(
        raw.get("encounterName") or raw.get("name") or raw.get("title") or "Imported Encounter"
    ).strip()

    raw_monsters = raw.get("monsters") or raw.get("creatures") or []
    if not isinstance(raw_monsters, list):
        raise ValueError(
            "File does not look like a D&D Beyond encounter export (no monster list found). "
            "Export from the Encounter Builder page."
        )

    monsters = []
    for m in raw_monsters:
        monster_name = str(
            m.get("name") or m.get("monsterName") or m.get("creature_name") or ""
        ).strip()
        if not monster_name:
            continue
        count = max(1, int(m.get("quantity") or m.get("count") or m.get("number") or 1))
        monsters.append({
            "name": monster_name,
            "count": count,
            "srd_monster": srd.find(monster_name),
        })

    if not monsters:
        raise ValueError("No valid monsters found in encounter file.")

    return {"encounter_name": encounter_name, "monsters": monsters}


def import_encounter(parsed: dict) -> dict:
    """Create DB entities from a parsed encounter result.

    Creates one encounter entity and one enemy entity per monster type
    (count > 1 is noted in the enemy name suffix and notes field).
    Each enemy is linked to the encounter via an 'involves' relationship.

    Returns a summary dict:
        {"encounter_id", "encounter_name", "created", "skipped_srd_lookup"}
    """
    encounter_id = db.create_entity(
        "encounter",
        parsed["encounter_name"],
        {"status": "Planned"},
        "Imported from D&D Beyond encounter builder.",
    )

    created = []
    skipped = []

    for m in parsed["monsters"]:
        count = m["count"]
        srd_monster = m["srd_monster"]
        name_suffix = f" (x{count})" if count > 1 else ""

        if srd_monster:
            prefill = srd.wizard_prefill(srd_monster)
            fields = {
                "cr": prefill["cr"],
                "creature_type": prefill["creature_type"],
                "sheet": shm.normalize_sheet({
                    "cr": prefill["cr"],
                    "creature_type": prefill["creature_type"],
                    "abilities": prefill.get("abilities", {}),
                    "saving_throw_proficiencies": prefill.get("saving_throw_proficiencies", []),
                    "skill_proficiencies": prefill.get("skill_proficiencies", {}),
                    "attacks": prefill.get("attacks", []),
                    "special_abilities": prefill.get("special_abilities", []),
                    "resistances": prefill.get("resistances", ""),
                    "immunities": prefill.get("immunities", ""),
                    "vulnerabilities": prefill.get("vulnerabilities", ""),
                    "ac": prefill["ac"],
                    "hp_max": prefill["hp_max"],
                }),
            }
            enemy_notes = f"Count: {count}" if count > 1 else ""
        else:
            fields = {"cr": "0", "creature_type": "Unknown"}
            enemy_notes = (
                f"Count: {count}. " if count > 1 else ""
            ) + "Not found in local SRD -- fill in stats manually."
            skipped.append(m["name"])

        enemy_id = db.create_entity("enemy", m["name"] + name_suffix, fields, enemy_notes)
        db.create_relationship(encounter_id, enemy_id, "involves", "")
        created.append(m["name"])

    return {
        "encounter_id": encounter_id,
        "encounter_name": parsed["encounter_name"],
        "created": created,
        "skipped_srd_lookup": skipped,
    }
