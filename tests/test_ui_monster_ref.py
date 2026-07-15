import asyncio
import db
from app import DMApp


def run(scenario):
    asyncio.run(scenario())


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()


def test_monster_ref_screen_opens(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(180, 50)) as pilot:
            await pilot.pause()
            await pilot.press("m")
            await pilot.pause()
            from screens.monster_ref import MonsterRefScreen
            assert isinstance(app.screen, MonsterRefScreen)

    run(scenario)


def test_monster_ref_list_populated(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(180, 50)) as pilot:
            await pilot.pause()
            await pilot.press("m")
            await pilot.pause()
            lv = app.screen.query_one("#monster-list")
            assert lv.__len__() > 0

    run(scenario)


def test_monster_ref_search_filters_list(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(180, 50)) as pilot:
            await pilot.pause()
            await pilot.press("m")
            await pilot.pause()
            screen = app.screen
            full_count = screen.query_one("#monster-list").__len__()
            screen.query_one("#monster-search").value = "troll"
            await pilot.pause()
            filtered_count = screen.query_one("#monster-list").__len__()
            assert filtered_count < full_count
            assert filtered_count == 1

    run(scenario)


def test_monster_ref_add_to_campaign_opens_wizard(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(180, 50)) as pilot:
            await pilot.pause()
            await pilot.press("m")
            await pilot.pause()
            # Select a monster and add it
            screen = app.screen
            screen.query_one("#btn-add-monster").press()
            for _ in range(4):
                await pilot.pause()
            from screens.wizard import WizardScreen
            assert isinstance(app.screen, WizardScreen)

    run(scenario)
