"""UI tests for Phase 14: condition library picker and death save tracking."""
import asyncio

import db
import combat as cbt
import conditions as cnd
from app import DMApp
from textual.widgets import Select, Input, ListView


def run(scenario):
    asyncio.run(scenario())


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    pc_id = db.create_entity("adventurer", "Mira Vex", {}, "")
    db.update_entity(pc_id, "Mira Vex", {
        "sheet": {"ac": 14, "hp_max": 18, "hp_current": 18, "abilities": {
            "str": 10, "dex": 14, "con": 13, "int": 12, "wis": 10, "cha": 8,
        }},
    }, "")
    db.create_entity("encounter", "Test Enc", {}, "")
    return pc_id


async def _open_combat(pilot, app):
    await pilot.press("c")
    await pilot.pause()
    app.screen.query_one("#entity-table").move_cursor(row=0)
    await pilot.pause()
    app.screen.action_open_selected()
    await pilot.pause()
    app.screen.action_open_combat()
    await pilot.pause()
    return app.screen


def test_condition_select_is_populated_from_library(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(140, 50)) as pilot:
            cs = await _open_combat(pilot, app)
            await pilot.press("tab")   # navigate to Attacks & HP tab
            await pilot.pause()
            cs.query_one("#combat-tabs").active = "tab-hp-conditions"
            await pilot.pause()
            sel = cs.query_one("#sel-condition-name", Select)
            option_values = [str(v) for _, v in sel._options]
            for name in cnd.CONDITION_NAMES:
                assert name in option_values, f"Missing condition: {name}"
            assert "__custom__" in option_values

    run(scenario)


def test_condition_description_appears_on_select(monkeypatch, tmp_path):
    pc_id = _setup(monkeypatch, tmp_path)

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(140, 50)) as pilot:
            cs = await _open_combat(pilot, app)
            cs.query_one("#combat-tabs").active = "tab-hp-conditions"
            await pilot.pause()
            cs.query_one("#sel-condition-name", Select).value = "Paralyzed"
            await pilot.pause()
            desc = str(cs.query_one("#condition-desc").content)
            assert "STR" in desc or "advantage" in desc.lower()

    run(scenario)


def test_applying_library_condition_adds_it_to_combatant(monkeypatch, tmp_path):
    pc_id = _setup(monkeypatch, tmp_path)

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(140, 50)) as pilot:
            cs = await _open_combat(pilot, app)
            cs.query_one("#sel-add-combatant", Select).value = str(pc_id)
            cs.query_one("#btn-add-combatant").press()
            await pilot.pause()
            cs.query_one("#combat-tabs").active = "tab-hp-conditions"
            await pilot.pause()
            cs.query_one("#sel-hp-target", Select).value = str(pc_id)
            cs.query_one("#sel-condition-name", Select).value = "Prone"
            cs.query_one("#btn-add-condition").press()
            await pilot.pause()
            combatant = next(c for c in cs.combat["combatants"] if c["entity_id"] == pc_id)
            assert any(c["name"] == "Prone" for c in combatant["conditions"])

    run(scenario)


def test_custom_condition_input_shows_when_custom_selected(monkeypatch, tmp_path):
    pc_id = _setup(monkeypatch, tmp_path)

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(140, 50)) as pilot:
            cs = await _open_combat(pilot, app)
            cs.query_one("#combat-tabs").active = "tab-hp-conditions"
            await pilot.pause()
            custom_input = cs.query_one("#input-condition-custom", Input)
            assert not custom_input.display
            cs.query_one("#sel-condition-name", Select).value = "__custom__"
            await pilot.pause()
            assert custom_input.display

    run(scenario)


def test_death_save_section_hidden_for_enemy(monkeypatch, tmp_path):
    pc_id = _setup(monkeypatch, tmp_path)
    enemy_id = db.create_entity("enemy", "Zombie", {}, "")
    db.update_entity(enemy_id, "Zombie", {
        "sheet": {"ac": 8, "hp_max": 10, "hp_current": 0},
    }, "")

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(140, 50)) as pilot:
            cs = await _open_combat(pilot, app)
            cs.query_one("#sel-add-combatant", Select).value = str(enemy_id)
            cs.query_one("#btn-add-combatant").press()
            await pilot.pause()
            cs.query_one("#combat-tabs").active = "tab-hp-conditions"
            await pilot.pause()
            cs.query_one("#sel-hp-target", Select).value = str(enemy_id)
            await pilot.pause()
            assert not cs.query_one("#death-save-section").display

    run(scenario)


def test_death_save_section_appears_when_adventurer_hits_zero(monkeypatch, tmp_path):
    pc_id = _setup(monkeypatch, tmp_path)

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(140, 50)) as pilot:
            cs = await _open_combat(pilot, app)
            cs.query_one("#sel-add-combatant", Select).value = str(pc_id)
            cs.query_one("#btn-add-combatant").press()
            await pilot.pause()
            cs.query_one("#combat-tabs").active = "tab-hp-conditions"
            await pilot.pause()
            cs.query_one("#sel-hp-target", Select).value = str(pc_id)
            await pilot.pause()
            # HP still > 0 — section should be hidden
            assert not cs.query_one("#death-save-section").display
            # Drive HP to 0 via apply damage
            cs.query_one("#input-hp-amount", Input).value = "18"
            cs.query_one("#btn-damage").press()
            await pilot.pause()
            assert cs.query_one("#death-save-section").display

    run(scenario)


def test_three_successes_adds_stable_condition(monkeypatch, tmp_path):
    pc_id = _setup(monkeypatch, tmp_path)
    # Pre-set HP to 0 directly in DB so we skip UI damage step
    entity = db.get_entity(pc_id)
    fields = dict(entity["fields"])
    sheet = dict(fields.get("sheet", {}))
    sheet["hp_current"] = 0
    fields["sheet"] = sheet
    db.update_entity(pc_id, entity["name"], fields, entity["notes"])

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(140, 50)) as pilot:
            cs = await _open_combat(pilot, app)
            cs.query_one("#sel-add-combatant", Select).value = str(pc_id)
            cs.query_one("#btn-add-combatant").press()
            await pilot.pause()
            cs.query_one("#combat-tabs").active = "tab-hp-conditions"
            await pilot.pause()
            cs.query_one("#sel-hp-target", Select).value = str(pc_id)
            await pilot.pause()
            cs.query_one("#btn-ds-success").press()
            cs.query_one("#btn-ds-success").press()
            cs.query_one("#btn-ds-success").press()
            await pilot.pause()
            combatant = next(c for c in cs.combat["combatants"] if c["entity_id"] == pc_id)
            assert any(c["name"] == "Stable" for c in combatant["conditions"])
            assert combatant["death_saves"] == {"successes": 0, "failures": 0}

    run(scenario)


def test_three_failures_adds_dead_condition(monkeypatch, tmp_path):
    pc_id = _setup(monkeypatch, tmp_path)
    entity = db.get_entity(pc_id)
    fields = dict(entity["fields"])
    sheet = dict(fields.get("sheet", {}))
    sheet["hp_current"] = 0
    fields["sheet"] = sheet
    db.update_entity(pc_id, entity["name"], fields, entity["notes"])

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(140, 50)) as pilot:
            cs = await _open_combat(pilot, app)
            cs.query_one("#sel-add-combatant", Select).value = str(pc_id)
            cs.query_one("#btn-add-combatant").press()
            await pilot.pause()
            cs.query_one("#combat-tabs").active = "tab-hp-conditions"
            await pilot.pause()
            cs.query_one("#sel-hp-target", Select).value = str(pc_id)
            await pilot.pause()
            cs.query_one("#btn-ds-failure").press()
            cs.query_one("#btn-ds-failure").press()
            cs.query_one("#btn-ds-failure").press()
            await pilot.pause()
            combatant = next(c for c in cs.combat["combatants"] if c["entity_id"] == pc_id)
            assert any(c["name"] == "Dead" for c in combatant["conditions"])
            assert combatant["death_saves"] == {"successes": 0, "failures": 0}

    run(scenario)
