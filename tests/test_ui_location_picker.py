"""UI tests for the 'location' field becoming a Select tied to real
Location entities (npc/session/encounter), instead of unconstrained free
text: a DM can now pick from existing locations, a newly created location
shows up next time the form opens, and a stale/unmatched value already
saved on an entity is preserved as its own option rather than silently
dropped when the form is reopened."""
import asyncio

import db
from app import DMApp
from screens.common import entity_ref_options
from textual.widgets import Input, Select


def run(scenario):
    asyncio.run(scenario())


def test_entity_ref_options_lists_existing_locations_by_name(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    db.create_entity("location", "Dockside Quarter", {}, "")
    db.create_entity("location", "The Sundered Anchor", {}, "")

    options = entity_ref_options("location")
    assert ("Dockside Quarter", "Dockside Quarter") in options
    assert ("The Sundered Anchor", "The Sundered Anchor") in options


def test_entity_ref_options_preserves_stale_unmatched_value(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    db.create_entity("location", "Dockside Quarter", {}, "")

    options = entity_ref_options("location", current_value="Some Deleted Place")
    values = [v for _, v in options]
    assert "Some Deleted Place" in values
    assert "Dockside Quarter" in values


def test_npc_form_location_select_includes_newly_created_location(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            await pilot.press("n")
            await pilot.pause()
            app.screen.action_add()
            await pilot.pause()
            form = app.screen
            sel = form.query_one("#field-location", Select)
            assert sel.value is Select.NULL
            assert all(v != "Dockside Quarter" for _, v in sel._options)
            await pilot.press("escape")
            await pilot.pause()

        # location created "elsewhere" (e.g. the Locations list) after that form opened
        db.create_entity("location", "Dockside Quarter", {}, "")

        async def scenario_two():
            app = DMApp()
            async with app.run_test(size=(120, 50)) as pilot:
                await pilot.pause()
                await pilot.press("n")
                await pilot.pause()
                app.screen.action_add()
                await pilot.pause()
                form = app.screen
                sel = form.query_one("#field-location", Select)
                assert any(v == "Dockside Quarter" for _, v in sel._options)

        await scenario_two()

    run(scenario)


def test_creating_npc_with_selected_location(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    db.create_entity("location", "Dockside Quarter", {}, "")

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            await pilot.press("n")
            await pilot.pause()
            app.screen.action_add()
            await pilot.pause()
            form = app.screen
            form.query_one("#field-name", Input).value = "Mira Thorn"
            form.query_one("#field-location", Select).value = "Dockside Quarter"
            form.action_save()
            await pilot.pause()

        npc = db.list_entities("npc")[0]
        assert npc["fields"]["location"] == "Dockside Quarter"

    run(scenario)


def test_editing_npc_with_stale_location_preserves_it_unless_changed(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    db.create_entity("location", "Dockside Quarter", {}, "")
    npc_id = db.create_entity("npc", "Mira Thorn", {"location": "Some Deleted Place"}, "")

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
            app.screen.action_edit()
            await pilot.pause()
            form = app.screen
            sel = form.query_one("#field-location", Select)
            assert sel.value == "Some Deleted Place"
            form.action_save()
            await pilot.pause()

        assert db.get_entity(npc_id)["fields"]["location"] == "Some Deleted Place"

    run(scenario)


def test_wizard_npc_location_step_uses_select(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    db.create_entity("location", "Dockside Quarter", {}, "")

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            await pilot.press("n")
            await pilot.pause()
            app.screen.action_wizard("quick")
            await pilot.pause()
            wiz = app.screen
            wiz.query_one("#wiz-name", Input).value = "Gareth"
            wiz.query_one("#wiz-location", Select).value = "Dockside Quarter"
            await wiz._go_next()  # basic_npc -> review
            await pilot.pause()
            await wiz._go_next()  # create
            await pilot.pause()

        npc = db.list_entities("npc")[0]
        assert npc["fields"]["location"] == "Dockside Quarter"

    run(scenario)
