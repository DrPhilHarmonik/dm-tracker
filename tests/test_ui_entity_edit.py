"""Regression test: EntityFormScreen.action_save() only collects the flat
schema fields (race, level, etc.), never sheet/active_effects/combat. Saving
an edit used to pass that incomplete dict straight to db.update_entity(),
which replaces the fields column wholesale -- silently wiping a character's
sheet, active effects, and combat data just from opening Edit and clicking
Save with no changes at all."""
import asyncio

import db
from app import DMApp


def run(scenario):
    asyncio.run(scenario())


def test_editing_flat_fields_preserves_sheet_and_active_effects(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    adv_id = db.create_entity("adventurer", "Test Hero", {"race": "Human", "level": "2"}, "")
    db.update_entity(adv_id, "Test Hero", {
        "race": "Human", "level": "2",
        "sheet": {
            "abilities": {"str": 16, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10},
            "ac": 18, "hp_max": 30, "hp_current": 30,
        },
        "active_effects": [{"source": "Bless", "stat": "cha", "modifier": 1, "rounds_remaining": 8}],
    }, "")

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
            detail.action_edit()
            await pilot.pause()
            form = app.screen
            # change one flat field, like a DM correcting a typo
            form.query_one("#field-race").value = "Half-Elf"
            form.action_save()
            await pilot.pause()

        fields = db.get_entity(adv_id)["fields"]
        assert fields["race"] == "Half-Elf"
        assert fields["sheet"]["ac"] == 18
        assert fields["sheet"]["hp_max"] == 30
        assert fields["active_effects"][0]["source"] == "Bless"

    run(scenario)


def test_editing_flat_level_syncs_into_sheet_level(monkeypatch, tmp_path):
    """The flat 'level' field (list columns, quick add) and fields['sheet']
    ['level'] (proficiency bonus math, Character Sheet) used to be two
    independent copies that only ever matched if both were set via the
    wizard at creation time. Editing one through the generic form left the
    other stale."""
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    adv_id = db.create_entity("adventurer", "Test Hero", {"level": "1"}, "")
    db.update_entity(adv_id, "Test Hero", {
        "level": "1",
        "sheet": {"abilities": {"str": 10, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10}, "level": 1},
    }, "")

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
            detail.action_edit()
            await pilot.pause()
            form = app.screen
            form.query_one("#field-level").value = "5"
            form.action_save()
            await pilot.pause()

        fields = db.get_entity(adv_id)["fields"]
        assert fields["level"] == "5"
        assert fields["sheet"]["level"] == 5

    run(scenario)


def test_saving_character_sheet_syncs_level_back_to_flat_field(monkeypatch, tmp_path):
    """The reverse direction: editing Level on the Character Sheet's Combat
    tab (the more common workflow) must update the flat field too, so list
    columns and the detail view's flat-fields section don't show a stale
    value."""
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    adv_id = db.create_entity("adventurer", "Test Hero", {"level": "1"}, "")
    db.update_entity(adv_id, "Test Hero", {
        "level": "1",
        "sheet": {"abilities": {"str": 10, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10}, "level": 1},
    }, "")

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
            detail.action_open_sheet()
            await pilot.pause()
            sheet_screen = app.screen
            sheet_screen.query_one("#sheet-level").value = "5"
            sheet_screen.action_save()
            await pilot.pause()

        fields = db.get_entity(adv_id)["fields"]
        assert fields["sheet"]["level"] == 5
        assert fields["level"] == "5"

    run(scenario)
