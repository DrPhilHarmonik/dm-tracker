"""UI interaction tests for the wizard's Race step (Phase 12): adventurer-
only, bakes ability/speed/senses/language bonuses into the created sheet,
and the Half-Elf choice-bonus sub-step appears/validates correctly."""
import asyncio

import db
import races
from app import DMApp
from textual.widgets import Input, Select


def run(scenario):
    asyncio.run(scenario())


def test_race_step_only_appears_for_adventurer_not_enemy(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            await pilot.press("a")
            await pilot.pause()
            app.screen.action_wizard("quick")
            await pilot.pause()
            wiz = app.screen
            assert "race" in wiz.steps
            await pilot.press("escape")
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()

            await pilot.press("x")
            await pilot.pause()
            app.screen.action_wizard("quick")
            await pilot.pause()
            wiz = app.screen
            assert "race" not in wiz.steps

    run(scenario)


def test_default_race_bakes_human_bonus_into_sheet(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            await pilot.press("a")
            await pilot.pause()
            app.screen.action_wizard("quick")
            await pilot.pause()
            wiz = app.screen
            wiz.query_one("#wiz-name", Input).value = "Brynn Ashforge"
            await wiz._go_next()  # basic -> race
            await pilot.pause()
            assert wiz.query_one("#wiz-race-select", Select).value == "Human"
            await wiz._go_next()  # race (default Human) -> class_or_cr
            await pilot.pause()
            await wiz._go_next()  # class_or_cr -> abilities (default Standard Array)
            await pilot.pause()
            await wiz._go_next()  # abilities -> review
            await pilot.pause()
            await wiz._go_next()  # create
            await pilot.pause()

        adv = db.list_entities("adventurer")[0]
        assert adv["fields"]["race"] == "Human"
        # Human: +1 to every ability, on top of the default Standard Array order
        assert adv["fields"]["sheet"]["abilities"] == {"str": 16, "dex": 15, "con": 14, "int": 13, "wis": 11, "cha": 9}
        assert adv["fields"]["sheet"]["speed"] == 30

    run(scenario)


def test_choosing_race_with_senses_bakes_speed_and_senses(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            await pilot.press("a")
            await pilot.pause()
            app.screen.action_wizard("quick")
            await pilot.pause()
            wiz = app.screen
            wiz.query_one("#wiz-name", Input).value = "Yarrow Fenn"
            await wiz._go_next()
            await pilot.pause()
            wiz.query_one("#wiz-race-select", Select).value = "Wood Elf"
            await pilot.pause()
            await wiz._go_next()
            await pilot.pause()
            await wiz._go_next()
            await pilot.pause()
            await wiz._go_next()
            await pilot.pause()
            await wiz._go_next()
            await pilot.pause()

        adv = db.list_entities("adventurer")[0]
        sheet = adv["fields"]["sheet"]
        assert sheet["speed"] == 35
        assert sheet["senses"] == "Darkvision 60 ft."
        assert sheet["languages"] == "Common, Elvish"
        # Wood Elf: +2 DEX, +1 WIS on top of the default Standard Array order
        assert sheet["abilities"]["dex"] == 16
        assert sheet["abilities"]["wis"] == 11

    run(scenario)


def test_half_elf_choice_bonus_step_appears_and_applies(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            await pilot.press("a")
            await pilot.pause()
            app.screen.action_wizard("quick")
            await pilot.pause()
            wiz = app.screen
            wiz.query_one("#wiz-name", Input).value = "Dorin Half-Tide"
            await wiz._go_next()
            await pilot.pause()
            wiz.query_one("#wiz-race-select", Select).value = "Half-Elf"
            await pilot.pause()
            assert wiz.query_one("#wiz-race-choice-0", Select) is not None
            assert wiz.query_one("#wiz-race-choice-1", Select) is not None
            wiz.query_one("#wiz-race-choice-0", Select).value = "str"
            wiz.query_one("#wiz-race-choice-1", Select).value = "con"
            await wiz._go_next()
            await pilot.pause()
            await wiz._go_next()
            await pilot.pause()
            await wiz._go_next()
            await pilot.pause()
            await wiz._go_next()
            await pilot.pause()

        adv = db.list_entities("adventurer")[0]
        abilities = adv["fields"]["sheet"]["abilities"]
        # default Standard Array order: str 15, dex 14, con 13, int 12, wis 10, cha 8
        assert abilities["str"] == 16  # chosen +1
        assert abilities["con"] == 14  # chosen +1
        assert abilities["cha"] == 10  # fixed +2
        assert abilities["dex"] == 14  # untouched

    run(scenario)


def test_half_elf_rejects_choosing_the_same_ability_twice(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            await pilot.press("a")
            await pilot.pause()
            app.screen.action_wizard("quick")
            await pilot.pause()
            wiz = app.screen
            wiz.query_one("#wiz-name", Input).value = "Dorin Half-Tide"
            await wiz._go_next()
            await pilot.pause()
            wiz.query_one("#wiz-race-select", Select).value = "Half-Elf"
            await pilot.pause()
            wiz.query_one("#wiz-race-choice-0", Select).value = "str"
            wiz.query_one("#wiz-race-choice-1", Select).value = "str"
            await wiz._go_next()
            await pilot.pause()

            assert wiz.steps[wiz.step_index] == "race"  # didn't advance
            assert "different abilities" in str(wiz.query_one("#wizard-error").content)

    run(scenario)


# -- Phase 13: class data bake-in -----------------------------------------

def test_wizard_bakes_proficiencies_hit_dice_and_spellcasting_into_sheet(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            await pilot.press("a")
            await pilot.pause()
            app.screen.action_wizard("quick")
            await pilot.pause()
            wiz = app.screen
            wiz.query_one("#wiz-name", Input).value = "Lyra Ashveil"
            await wiz._go_next()   # basic -> race
            await pilot.pause()
            wiz.query_one("#wiz-race-select", Select).value = "High Elf"
            await wiz._go_next()   # race -> class_or_cr
            await pilot.pause()
            wiz.query_one("#wiz-class", Select).value = "Wizard"
            wiz.query_one("#wiz-level", Input).value = "3"
            await wiz._go_next()   # class_or_cr -> abilities
            await pilot.pause()
            await wiz._go_next()   # abilities -> review
            await pilot.pause()
            await wiz._go_next()   # create
            await pilot.pause()

    run(scenario)

    adv = db.list_entities("adventurer")[0]
    sheet = adv["fields"]["sheet"]
    assert sheet["hit_dice"] == "3d6"
    assert sheet["spellcasting_ability"] == "int"
    assert "light crossbows" in sheet["proficiencies"]


def test_non_caster_has_no_spellcasting_ability_on_sheet(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            await pilot.press("a")
            await pilot.pause()
            app.screen.action_wizard("quick")
            await pilot.pause()
            wiz = app.screen
            wiz.query_one("#wiz-name", Input).value = "Gorrak"
            await wiz._go_next()   # basic -> race
            await pilot.pause()
            await wiz._go_next()   # race (default Human) -> class_or_cr
            await pilot.pause()
            wiz.query_one("#wiz-class", Select).value = "Barbarian"
            await wiz._go_next()   # class_or_cr -> abilities
            await pilot.pause()
            await wiz._go_next()   # abilities -> review
            await pilot.pause()
            await wiz._go_next()   # create
            await pilot.pause()

    run(scenario)

    adv = db.list_entities("adventurer")[0]
    sheet = adv["fields"]["sheet"]
    assert sheet["hit_dice"] == "1d12"
    assert sheet.get("spellcasting_ability", "") == ""
    assert "martial weapons" in sheet["proficiencies"]
