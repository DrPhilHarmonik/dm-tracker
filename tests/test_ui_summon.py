"""UI integration tests for Phase 11b: Summon Creature flow.

The summon flow:
  1. Pick a summoner from the Select on the Turn Controls tab.
  2. Click "Open Summon Wizard" -> WizardScreen opens.
  3. Wizard is dismissed with the new entity_id.
  4. Callback creates "summoned by" relationship and adds creature to combat.
"""
import asyncio

import combat as cbt
import db
from app import DMApp
from screens.combat import CombatTrackerScreen
from textual.widgets import TabbedContent, Select


def run(scenario):
    asyncio.run(scenario())


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    pc_id = db.create_entity("adventurer", "Mira the Mage", {
        "level": "5",
        "sheet": {"abilities": {"str": 8, "dex": 14, "con": 12, "int": 16, "wis": 12, "cha": 10},
                  "ac": 12, "hp_max": 30, "hp_current": 30, "level": 5, "spellcasting_ability": "int"},
    }, "")
    combat_state = cbt.add_combatant(cbt.default_combat(), pc_id)
    enc_id = db.create_entity("encounter", "Mage Fight", {"status": "Planned", "combat": combat_state}, "")
    return pc_id, enc_id


def test_summon_section_renders(monkeypatch, tmp_path):
    pc_id, enc_id = _setup(monkeypatch, tmp_path)

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(140, 50)) as pilot:
            await pilot.pause()
            await app.push_screen(CombatTrackerScreen(enc_id))
            await pilot.pause(0.3)
            app.screen.query_one("#combat-tabs", TabbedContent).active = "tab-turn-controls"
            await pilot.pause(0.1)
            # Summon Select and button must exist
            sel = app.screen.query_one("#sel-summon-caster", Select)
            btn = app.screen.query_one("#btn-summon")
            assert sel is not None
            assert btn is not None

    run(scenario)


def test_summon_creates_relationship_and_adds_to_combat(monkeypatch, tmp_path):
    pc_id, enc_id = _setup(monkeypatch, tmp_path)

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(140, 50)) as pilot:
            await pilot.pause()
            cs = CombatTrackerScreen(enc_id)
            await app.push_screen(cs)
            await pilot.pause(0.3)

            # Set summoner then invoke the callback directly (bypassing wizard UI)
            summon_id = db.create_entity("enemy", "Fire Elemental", {
                "cr": "5", "creature_type": "Elemental",
                "sheet": {"abilities": {"str": 18, "dex": 13, "con": 14, "int": 6, "wis": 10, "cha": 7},
                          "ac": 13, "hp_max": 102, "hp_current": 102, "cr": "5"},
            }, "")

            cs._pending_summoner_id = pc_id
            cs._on_summon_created(summon_id)
            await pilot.pause(0.1)

            # Relationship created
            rels = db.get_relationships(summon_id)
            assert any(r["rel_type"] == "summoned by" for r in rels), \
                f"Expected 'summoned by' rel, got: {[r['rel_type'] for r in rels]}"

            # Summon is now in the encounter
            enc = db.get_entity(enc_id)
            combatant_ids = [c["entity_id"] for c in enc["fields"]["combat"]["combatants"]]
            assert summon_id in combatant_ids

    run(scenario)


def test_summon_is_linked_to_correct_summoner(monkeypatch, tmp_path):
    pc_id, enc_id = _setup(monkeypatch, tmp_path)
    # Add a second adventurer
    other_id = db.create_entity("adventurer", "Tank the Warrior", {"level": "5"}, "")

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(140, 50)) as pilot:
            await pilot.pause()
            cs = CombatTrackerScreen(enc_id)
            await app.push_screen(cs)
            await pilot.pause(0.3)

            summon_id = db.create_entity("enemy", "Wolf", {
                "cr": "1/4", "creature_type": "Beast",
                "sheet": {"abilities": {"str": 12, "dex": 15, "con": 12, "int": 3, "wis": 12, "cha": 6},
                          "ac": 13, "hp_max": 11, "hp_current": 11, "cr": "1/4"},
            }, "")

            # pc_id is the summoner, not other_id
            cs._pending_summoner_id = pc_id
            cs._on_summon_created(summon_id)
            await pilot.pause(0.1)

            rels = db.get_relationships(summon_id)
            summoned_by = [r for r in rels if r["rel_type"] == "summoned by"]
            assert len(summoned_by) == 1
            # The related entity should be the summoner (Mira), not Tank
            assert summoned_by[0]["to_id"] == pc_id

    run(scenario)
