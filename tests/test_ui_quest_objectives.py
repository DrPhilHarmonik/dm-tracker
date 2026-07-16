"""UI tests for Phase 26 quest objectives."""
import asyncio

import db
from app import DMApp


def run(scenario):
    asyncio.run(scenario())


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()


async def _open_quest_detail(pilot, app):
    await pilot.press("q")
    await pilot.pause()
    table = app.screen.query_one("#entity-table")
    table.move_cursor(row=0)
    await pilot.pause()
    app.screen.action_open_selected()
    await pilot.pause()
    return app.screen


def test_quest_detail_adds_and_toggles_objective(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    quest_id = db.create_entity("quest", "Find the Moon Key", {"status": "Active"}, "")

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            detail = await _open_quest_detail(pilot, app)

            detail.action_add_objective()
            await pilot.pause()
            modal = app.screen
            modal.query_one("#objective-text").value = "Recover the key"
            modal.action_save()
            await pilot.pause()

            detail = app.screen
            table = detail.query_one("#objectives-table")
            assert table.row_count == 1
            assert str(table.get_cell_at((0, 0))) == "No"
            assert str(table.get_cell_at((0, 1))) == "Recover the key"

            table.move_cursor(row=0)
            detail.action_toggle_objective()
            await pilot.pause()

            assert str(table.get_cell_at((0, 0))) == "Yes"

        assert db.get_entity(quest_id)["fields"]["objectives"] == [
            {"text": "Recover the key", "done": True}
        ]

    run(scenario)


def test_quest_list_shows_objective_progress(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    db.create_entity(
        "quest",
        "Find the Moon Key",
        {
            "status": "Active",
            "difficulty": "Medium",
            "objectives": [
                {"text": "Recover the key", "done": True},
                {"text": "Return to Mira", "done": False},
            ],
        },
        "",
    )

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            await pilot.press("q")
            await pilot.pause()

            table = app.screen.query_one("#entity-table")
            assert str(table.get_cell_at((0, 3))) == "1 / 2 complete"

    run(scenario)
