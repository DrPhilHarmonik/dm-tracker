"""Regression tests for screen callback/dismissal behavior.

This exact class of bug has bitten the app twice already: Textual's
app.pop_screen() silently discards any callback registered via
push_screen(..., callback=...) without invoking it, and Select.set_options()
always resets the widget's current selection. These tests drive the real
DMApp through a headless Pilot session so a regression on either front
fails loudly instead of silently never refreshing a caller screen.
"""
import asyncio

import db
from app import DMApp


def run(scenario):
    asyncio.run(scenario())


def test_escaping_entity_detail_refreshes_the_caller_list(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    db.create_entity("npc", "Old Name", {}, "")

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
            detail = app.screen
            detail.action_edit()
            await pilot.pause()
            form = app.screen
            form.query_one("#field-name").value = "New Name"
            form.action_save()
            await pilot.pause()

            await pilot.press("escape")
            await pilot.pause()
            list_screen = app.screen
            assert list_screen is not detail
            cell = list_screen.query_one("#entity-table").get_cell_at((0, 0))
            assert "New Name" in str(cell)

    run(scenario)


def test_escaping_combat_tracker_refreshes_the_caller_detail(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    enc_id = db.create_entity("encounter", "Tavern Brawl", {"status": "Planned"}, "")

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            await pilot.press("c")
            await pilot.pause()
            table = app.screen.query_one("#entity-table")
            table.move_cursor(row=0)
            await pilot.pause()
            app.screen.action_open_selected()
            await pilot.pause()
            detail = app.screen
            assert "Planned" in detail.query_one("#detail-body").content

            detail.action_open_combat()
            await pilot.pause()
            combat_screen = app.screen
            combat_screen.query_one("#btn-start-encounter").press()
            await pilot.pause()

            await pilot.press("escape")
            await pilot.pause()
            assert app.screen is detail
            assert "Active" in detail.query_one("#detail-body").content

    run(scenario)


def test_escaping_effects_screen_refreshes_the_caller_detail(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    adv_id = db.create_entity("adventurer", "Mira Thorn", {}, "")

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            await pilot.press("a")
            await pilot.pause()
            table = app.screen.query_one("#entity-table")
            table.move_cursor(row=0)
            await pilot.pause()
            app.screen.action_open_selected()
            await pilot.pause()
            detail = app.screen
            assert "Active Effects" not in detail.query_one("#detail-body").content

            detail.action_open_effects()
            await pilot.pause()
            fxscreen = app.screen
            fxscreen.query_one("#input-effect-source").value = "Potion of Speed"
            fxscreen.query_one("#sel-effect-stat").value = "dex"
            fxscreen.query_one("#input-effect-modifier").value = "2"
            fxscreen.query_one("#btn-add-effect").press()
            await pilot.pause()

            await pilot.press("escape")
            await pilot.pause()
            assert app.screen is detail
            assert "Active Effects" in detail.query_one("#detail-body").content
            assert "Potion of Speed" in detail.query_one("#detail-body").content

    run(scenario)


def test_select_set_options_preserves_selection_across_combat_actions(monkeypatch, tmp_path):
    """Regression for the bug where refreshing the combatant dropdowns after
    every action wiped whichever combatant the DM had selected, silently
    no-op'ing the next sequential action (e.g. adding a 2nd condition)."""
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    adv_id = db.create_entity("adventurer", "Mira Thorn", {}, "")
    enc_id = db.create_entity("encounter", "Test Fight", {}, "")

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            await pilot.press("c")
            await pilot.pause()
            table = app.screen.query_one("#entity-table")
            table.move_cursor(row=0)
            await pilot.pause()
            app.screen.action_open_selected()
            await pilot.pause()
            app.screen.action_open_combat()
            await pilot.pause()
            cs = app.screen

            cs.query_one("#sel-add-combatant").value = str(adv_id)
            cs.query_one("#btn-add-combatant").press()
            await pilot.pause()

            cs.query_one("#sel-hp-target").value = str(adv_id)
            cs.query_one("#input-condition-name").value = "Stunned"
            cs.query_one("#btn-add-condition").press()
            await pilot.pause()
            # the selection must survive _persist()'s dropdown refresh for
            # this second add to actually target Mira, not silently no-op
            cs.query_one("#input-condition-name").value = "Blinded"
            cs.query_one("#btn-add-condition").press()
            await pilot.pause()

            conditions = cs.combat["combatants"][0]["conditions"]
            assert [c["name"] for c in conditions] == ["Stunned", "Blinded"]

    run(scenario)
