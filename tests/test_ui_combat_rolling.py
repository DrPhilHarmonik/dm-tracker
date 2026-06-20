"""UI interaction tests for the Combat Tracker's integrated attack/damage
rolling (Attacks & HP tab): the attacker should default to whoever's turn
it is, the first available attack should auto-select rather than sitting
blank, and a damage roll should pre-fill the HP-apply field so a full
turn (roll to-hit -> roll damage -> apply -> next turn) never requires
leaving this one screen.
"""
import asyncio

import db
from app import DMApp


def run(scenario):
    asyncio.run(scenario())


def _make_combat(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    pc_id = db.create_entity("adventurer", "Brynn Ashforge", {}, "")
    db.update_entity(pc_id, "Brynn Ashforge", {
        "sheet": {
            "abilities": {"str": 15, "dex": 13, "con": 14, "int": 10, "wis": 12, "cha": 8},
            "ac": 16, "hp_max": 20, "hp_current": 20,
            "attacks": [{"name": "Longsword", "bonus": 4, "damage": "1d8+2", "damage_type": "slashing"}],
        },
    }, "")
    enemy_id = db.create_entity("enemy", "Goblin Boss", {}, "")
    db.update_entity(enemy_id, "Goblin Boss", {
        "sheet": {
            "abilities": {"str": 14, "dex": 14, "con": 12, "int": 8, "wis": 8, "cha": 10},
            "ac": 14, "hp_max": 21, "hp_current": 21,
            "attacks": [{"name": "Scimitar", "bonus": 4, "damage": "1d6+2", "damage_type": "slashing"}],
        },
    }, "")
    db.create_entity("encounter", "Test Fight", {}, "")
    return pc_id, enemy_id


async def _open_combat_tracker(pilot, app):
    await pilot.press("c")
    await pilot.pause()
    table = app.screen.query_one("#entity-table")
    table.move_cursor(row=0)
    await pilot.pause()
    app.screen.action_open_selected()
    await pilot.pause()
    app.screen.action_open_combat()
    await pilot.pause()
    return app.screen


def test_attacker_defaults_to_current_turn_and_first_attack_auto_selects(monkeypatch, tmp_path):
    pc_id, enemy_id = _make_combat(monkeypatch, tmp_path)

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            cs = await _open_combat_tracker(pilot, app)

            cs.query_one("#sel-add-combatant").value = str(pc_id)
            cs.query_one("#btn-add-combatant").press()
            await pilot.pause()
            cs.query_one("#sel-add-combatant").value = str(enemy_id)
            cs.query_one("#btn-add-combatant").press()
            await pilot.pause()

            cs.query_one("#sel-initiative-target").value = str(pc_id)
            cs.query_one("#input-initiative").value = "20"
            cs.query_one("#btn-set-initiative").press()
            await pilot.pause()
            cs.query_one("#sel-initiative-target").value = str(enemy_id)
            cs.query_one("#input-initiative").value = "10"
            cs.query_one("#btn-set-initiative").press()
            await pilot.pause()

            cs.query_one("#btn-start-encounter").press()
            await pilot.pause()

            assert cs.query_one("#sel-attack-attacker").value == str(pc_id)
            assert cs.query_one("#sel-attack-choice").value == "0"

    run(scenario)


def test_roll_to_hit_reports_hit_or_miss_against_target_ac(monkeypatch, tmp_path):
    pc_id, enemy_id = _make_combat(monkeypatch, tmp_path)

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            cs = await _open_combat_tracker(pilot, app)

            cs.query_one("#sel-add-combatant").value = str(pc_id)
            cs.query_one("#btn-add-combatant").press()
            await pilot.pause()
            cs.query_one("#sel-add-combatant").value = str(enemy_id)
            cs.query_one("#btn-add-combatant").press()
            await pilot.pause()
            cs.query_one("#btn-start-encounter").press()
            await pilot.pause()

            cs.query_one("#sel-hp-target").value = str(enemy_id)
            await pilot.pause()
            cs.query_one("#btn-roll-attack-hit").press()
            await pilot.pause()

            result = str(cs.query_one("#attack-roll-result").content)
            assert "Longsword to-hit" in result
            assert "AC 14" in result
            assert "HIT" in result or "MISS" in result

    run(scenario)


def test_roll_damage_prefills_hp_amount_for_one_click_apply(monkeypatch, tmp_path):
    pc_id, enemy_id = _make_combat(monkeypatch, tmp_path)

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            cs = await _open_combat_tracker(pilot, app)

            cs.query_one("#sel-add-combatant").value = str(pc_id)
            cs.query_one("#btn-add-combatant").press()
            await pilot.pause()
            cs.query_one("#sel-add-combatant").value = str(enemy_id)
            cs.query_one("#btn-add-combatant").press()
            await pilot.pause()
            cs.query_one("#btn-start-encounter").press()
            await pilot.pause()

            cs.query_one("#sel-hp-target").value = str(enemy_id)
            await pilot.pause()
            cs.query_one("#btn-roll-attack-hit").press()
            await pilot.pause()
            cs.query_one("#btn-roll-attack-damage").press()
            await pilot.pause()

            prefilled = cs.query_one("#input-hp-amount").value
            assert prefilled.isdigit() and int(prefilled) > 0

            cs.query_one("#btn-damage").press()
            await pilot.pause()
            goblin_hp = db.get_entity(enemy_id)["fields"]["sheet"]["hp_current"]
            assert goblin_hp == 21 - int(prefilled)

    run(scenario)


def test_next_turn_switches_attacker_and_their_attack_choice(monkeypatch, tmp_path):
    pc_id, enemy_id = _make_combat(monkeypatch, tmp_path)

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            cs = await _open_combat_tracker(pilot, app)

            cs.query_one("#sel-add-combatant").value = str(pc_id)
            cs.query_one("#btn-add-combatant").press()
            await pilot.pause()
            cs.query_one("#sel-add-combatant").value = str(enemy_id)
            cs.query_one("#btn-add-combatant").press()
            await pilot.pause()
            cs.query_one("#sel-initiative-target").value = str(pc_id)
            cs.query_one("#input-initiative").value = "20"
            cs.query_one("#btn-set-initiative").press()
            await pilot.pause()
            cs.query_one("#sel-initiative-target").value = str(enemy_id)
            cs.query_one("#input-initiative").value = "10"
            cs.query_one("#btn-set-initiative").press()
            await pilot.pause()
            cs.query_one("#btn-start-encounter").press()
            await pilot.pause()
            assert cs.query_one("#sel-attack-attacker").value == str(pc_id)

            cs.query_one("#btn-next-turn").press()
            await pilot.pause()
            assert cs.query_one("#sel-attack-attacker").value == str(enemy_id)
            assert cs.query_one("#sel-attack-choice").value == "0"  # Goblin's Scimitar, auto-selected

    run(scenario)
