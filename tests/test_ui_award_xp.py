import asyncio
import db
from app import DMApp
import xp as xpm


def run(scenario):
    asyncio.run(scenario())


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()


def test_award_xp_screen_opens(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+x")
            await pilot.pause()
            from screens.award_xp import AwardXPScreen
            assert isinstance(app.screen, AwardXPScreen)

    run(scenario)


def test_award_xp_no_adventurers_shows_dim_label(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+x")
            await pilot.pause()
            label = app.screen.query_one("#xp-split-label").content
            assert "No active" in str(label)

    run(scenario)


def test_award_xp_split_label_updates_on_input(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    db.create_entity("adventurer", "Fighter", {"status": "Active"}, "")
    db.create_entity("adventurer", "Cleric", {"status": "Active"}, "")

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+x")
            await pilot.pause()
            inp = app.screen.query_one("#xp-input")
            inp.value = "600"
            await pilot.pause()
            label = str(app.screen.query_one("#xp-split-label").content)
            assert "300" in label

    run(scenario)


def test_award_xp_persists_to_entities(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = db.create_entity("adventurer", "Aria", {"status": "Active", "xp": 0}, "")

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+x")
            await pilot.pause()
            screen = app.screen
            screen.query_one("#xp-input").value = "500"
            await pilot.pause()
            screen.query_one("#btn-award").press()
            await pilot.pause()

        entity = db.get_entity(eid)
        assert entity["fields"]["xp"] == 500

    run(scenario)


def test_award_xp_splits_evenly(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    id1 = db.create_entity("adventurer", "PC1", {"status": "Active", "xp": 0}, "")
    id2 = db.create_entity("adventurer", "PC2", {"status": "Active", "xp": 0}, "")
    id3 = db.create_entity("adventurer", "PC3", {"status": "Active", "xp": 0}, "")

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+x")
            await pilot.pause()
            screen = app.screen
            screen.query_one("#xp-input").value = "300"
            await pilot.pause()
            screen.query_one("#btn-award").press()
            await pilot.pause()

        for eid in (id1, id2, id3):
            assert db.get_entity(eid)["fields"]["xp"] == 100

    run(scenario)


def test_award_xp_level_up_message_shown(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    # PC at level 1 with 0 XP; awarding 300 XP should trigger level up
    db.create_entity("adventurer", "Hero", {"status": "Active", "xp": 0, "level": "1"}, "")

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+x")
            await pilot.pause()
            screen = app.screen
            screen.query_one("#xp-input").value = "300"
            await pilot.pause()
            screen.query_one("#btn-award").press()
            await pilot.pause()
            result = str(app.screen.query_one("#xp-result").content)
            assert "Level up" in result or "LEVEL UP" in result

    run(scenario)
