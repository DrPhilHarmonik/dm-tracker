"""UI interaction tests for the creation wizard: cancellation must leave no
orphaned data behind, and the wizard buttons must only appear for the
entity types the wizard actually knows how to build.
"""
import asyncio

import db
from app import DMApp
from screens.wizard import WIZARD_ENTITY_TYPES


def run(scenario):
    asyncio.run(scenario())


def test_wizard_escape_creates_nothing_and_returns_to_the_list(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            await pilot.press("a")
            await pilot.pause()
            list_screen = app.screen
            list_screen.action_wizard("quick")
            await pilot.pause()
            wiz = app.screen
            wiz.query_one("#wiz-name").value = "Should Not Exist"
            await pilot.press("escape")
            await pilot.pause()
            assert app.screen is list_screen
            assert db.list_entities("adventurer") == []

    run(scenario)


def test_make_hostile_no_creates_nothing(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    db.create_entity("npc", "Gareth the Merchant", {}, "")

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            await pilot.press("n")
            await pilot.pause()
            table = app.screen.query_one("#entity-table")
            table.move_cursor(row=0)
            await pilot.pause()
            app.screen.action_open_selected()
            await pilot.pause()
            npc_detail = app.screen
            npc_detail.action_make_hostile()
            await pilot.pause()
            await pilot.click("#btn-no")
            await pilot.pause()
            assert app.screen is npc_detail
            assert db.list_entities("enemy") == []

    run(scenario)


def test_make_hostile_yes_then_wizard_cancel_creates_nothing(monkeypatch, tmp_path):
    """Cancelling out of the wizard mid-way through Make Hostile must not
    leave a half-created Enemy or a dangling relationship behind."""
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    db.create_entity("npc", "Gareth the Merchant", {}, "")

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            await pilot.press("n")
            await pilot.pause()
            table = app.screen.query_one("#entity-table")
            table.move_cursor(row=0)
            await pilot.pause()
            app.screen.action_open_selected()
            await pilot.pause()
            npc_detail = app.screen
            npc_detail.action_make_hostile()
            await pilot.pause()
            await pilot.click("#btn-yes")
            await pilot.pause()
            wiz = app.screen
            assert wiz.link_to_npc_id is not None

            await pilot.press("escape")
            await pilot.pause()
            assert app.screen is npc_detail
            assert db.list_entities("enemy") == []
            assert db.list_relationships() == []

    run(scenario)


def test_wizard_buttons_only_appear_for_supported_entity_types(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            for key, type_name in [
                ("l", "location"), ("q", "quest"), ("f", "faction"),
                ("i", "item"), ("s", "session"), ("c", "encounter"),
                ("n", "npc"), ("a", "adventurer"), ("x", "enemy"),
            ]:
                await pilot.press(key)
                await pilot.pause()
                ids = [w.id for w in app.screen.query("*") if w.id]
                expected = type_name in WIZARD_ENTITY_TYPES
                assert ("btn-wizard-quick" in ids) == expected, type_name
                await pilot.press("escape")
                await pilot.pause()

    run(scenario)
