"""UI tests for Phase 27 relationship browser."""
import asyncio

import db
from app import DMApp


def run(scenario):
    asyncio.run(scenario())


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()


def _seed_relationships():
    npc_id = db.create_entity("npc", "Mira Thorn", {"race": "Human"}, "")
    quest_id = db.create_entity("quest", "Find the Moon Key", {"status": "Active"}, "")
    faction_id = db.create_entity("faction", "Silver Circle", {}, "")
    db.create_relationship(npc_id, quest_id, "gave quest", "")
    return npc_id, quest_id, faction_id


def test_relationship_browser_opens_from_dashboard(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _seed_relationships()

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            app.screen.action_relationship_browser()
            await pilot.pause()

            from screens.relationships import RelationshipBrowserScreen
            assert isinstance(app.screen, RelationshipBrowserScreen)
            table = app.screen.query_one("#relationship-table")
            assert table.row_count >= 3

    run(scenario)


def test_relationship_browser_filters_by_entity_type(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _seed_relationships()

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            app.screen.action_relationship_browser()
            await pilot.pause()

            screen = app.screen
            screen.query_one("#relationship-type-filter").value = "quest"
            await pilot.pause()
            table = screen.query_one("#relationship-table")

            assert table.row_count == 1
            assert str(table.get_cell_at((0, 0))) == "Find the Moon Key"
            assert str(table.get_cell_at((0, 1))) == "Quest"

    run(scenario)


def test_relationship_browser_opens_related_entity_from_row(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _seed_relationships()

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            app.screen.action_relationship_browser()
            await pilot.pause()

            table = app.screen.query_one("#relationship-table")
            table.move_cursor(row=0)
            await pilot.pause()
            app.screen.action_open_selected()
            await pilot.pause()

            from screens.entities import EntityDetailScreen
            assert isinstance(app.screen, EntityDetailScreen)
            assert app.screen.title == "Find the Moon Key"

    run(scenario)


def test_relationship_browser_opens_from_entity_detail(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    npc_id, _, _ = _seed_relationships()

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            await pilot.press("n")
            await pilot.pause()
            app.screen.action_open_selected()
            await pilot.pause()
            detail = app.screen
            assert detail.entity_id == npc_id

            detail.action_relationship_browser()
            await pilot.pause()

            from screens.relationships import RelationshipBrowserScreen
            assert isinstance(app.screen, RelationshipBrowserScreen)

    run(scenario)
