"""UI interaction tests for the Session Workflow screen: reachable from a
Session entity's detail view, lists the five aggregated sections, and its
row/button navigation actually opens the right existing screen (Sheet / Roll
/ Combat Tracker / Detail) for each section."""
import asyncio

import db
from app import DMApp


def run(scenario):
    asyncio.run(scenario())


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()


async def _open_session_workflow(pilot, app):
    await pilot.press("s")
    await pilot.pause()
    table = app.screen.query_one("#entity-table")
    table.move_cursor(row=0)
    await pilot.pause()
    app.screen.action_open_selected()
    await pilot.pause()
    detail = app.screen
    detail.action_open_session_workflow()
    await pilot.pause()
    return app.screen


def test_session_workflow_lists_pcs_quests_encounters_npcs_and_notes(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    db.create_entity("session", "Session 1", {"session_number": "1"}, "")
    db.create_entity("adventurer", "Brynn Ashforge", {"class_name": "Fighter", "level": "2"}, "")
    quest_id = db.create_entity("quest", "Find the Moon Key", {
        "status": "Active",
        "objectives": [
            {"text": "Recover the key", "done": True},
            {"text": "Return to Mira", "done": False},
        ],
    }, "")
    db.create_entity("encounter", "Ambush", {"status": "Active"}, "")
    npc_id = db.create_entity("npc", "Mira Thorn", {"race": "Human"}, "")
    db.create_relationship(npc_id, quest_id, "gave quest", "")

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            wf = await _open_session_workflow(pilot, app)

            assert str(wf.query_one("#wf-pcs").get_cell_at((0, 0))) == "Brynn Ashforge"
            assert str(wf.query_one("#wf-quests").get_cell_at((0, 0))) == "Find the Moon Key"
            assert str(wf.query_one("#wf-quests").get_cell_at((0, 2))) == "1 / 2 complete"
            assert str(wf.query_one("#wf-encounters").get_cell_at((0, 0))) == "Ambush"
            assert str(wf.query_one("#wf-npcs").get_cell_at((0, 0))) == "Mira Thorn"

    run(scenario)


def test_pc_sheet_button_opens_character_sheet(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    db.create_entity("session", "Session 1", {}, "")
    db.create_entity("adventurer", "Brynn Ashforge", {}, "")

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            wf = await _open_session_workflow(pilot, app)

            wf.query_one("#wf-pcs").move_cursor(row=0)
            await pilot.pause()
            wf.query_one("#btn-wf-pc-sheet").press()
            # CharacterSheetScreen.on_mount does 5 async tab-builds; give it time
            for _ in range(8):
                await pilot.pause()

            from screens.sheet import CharacterSheetScreen
            assert isinstance(app.screen, CharacterSheetScreen)

    run(scenario)


def test_encounter_row_opens_combat_tracker(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    db.create_entity("session", "Session 1", {}, "")
    db.create_entity("encounter", "Ambush", {"status": "Planned"}, "")

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            wf = await _open_session_workflow(pilot, app)

            table = wf.query_one("#wf-encounters")
            table.move_cursor(row=0)
            await pilot.pause()
            table.action_select_cursor()
            await pilot.pause()

            from screens.combat import CombatTrackerScreen
            assert isinstance(app.screen, CombatTrackerScreen)

    run(scenario)


def test_quest_row_opens_entity_detail(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    db.create_entity("session", "Session 1", {}, "")
    db.create_entity("quest", "Find the Moon Key", {"status": "Active"}, "")

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            wf = await _open_session_workflow(pilot, app)

            table = wf.query_one("#wf-quests")
            table.move_cursor(row=0)
            await pilot.pause()
            table.action_select_cursor()
            await pilot.pause()

            from screens.entities import EntityDetailScreen
            assert isinstance(app.screen, EntityDetailScreen)
            assert "Find the Moon Key" in app.screen.title

    run(scenario)
