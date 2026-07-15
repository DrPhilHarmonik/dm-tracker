import asyncio
import db
from app import DMApp
from screens.party_overview import _hp_cell, _get_combat_conditions, _format_slots
import sheet as shm


def run(scenario):
    asyncio.run(scenario())


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()


# -- unit tests for helpers --------------------------------------------------

def test_hp_cell_green_above_half():
    t = _hp_cell(30, 40)
    assert "30/40" in t.plain
    assert t.style == "green"


def test_hp_cell_yellow_between_quarter_and_half():
    t = _hp_cell(8, 30)
    assert t.style == "yellow"


def test_hp_cell_red_at_quarter_or_below():
    t = _hp_cell(5, 30)
    assert t.style == "red"


def test_hp_cell_bold_red_at_zero():
    t = _hp_cell(0, 30)
    assert t.style == "bold red"


def test_hp_cell_dim_when_max_zero():
    t = _hp_cell(0, 0)
    assert t.style == "dim"


def test_format_slots_shows_nonzero_max_levels():
    sheet = shm.normalize_sheet({
        "spell_slots": {
            "1": {"current": 3, "max": 4},
            "2": {"current": 0, "max": 2},
            **{str(i): {"current": 0, "max": 0} for i in range(3, 10)},
        }
    })
    result = _format_slots(sheet)
    assert "L1:3/4" in result
    assert "L2:0/2" in result
    assert "L3" not in result


def test_format_slots_empty_when_no_slots():
    sheet = shm.normalize_sheet({})
    assert _format_slots(sheet) == ""


def test_get_combat_conditions_only_from_started_encounters(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    pc_id = db.create_entity("adventurer", "Fighter", {}, "")
    # unstarted encounter -- conditions should NOT appear
    db.create_entity("encounter", "Enc1", {
        "combat": {
            "round": 1, "turn_index": 0, "started": False,
            "combatants": [{"entity_id": pc_id, "initiative": 10,
                            "conditions": [{"name": "Poisoned", "rounds_remaining": 2}],
                            "death_saves": {"successes": 0, "failures": 0},
                            "actions_used": {}}]
        }
    }, "")
    result = _get_combat_conditions()
    assert pc_id not in result


def test_get_combat_conditions_returns_conditions_from_started_encounter(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    pc_id = db.create_entity("adventurer", "Wizard", {}, "")
    db.create_entity("encounter", "Enc1", {
        "combat": {
            "round": 2, "turn_index": 0, "started": True,
            "combatants": [{"entity_id": pc_id, "initiative": 15,
                            "conditions": [{"name": "Stunned", "rounds_remaining": 1}],
                            "death_saves": {"successes": 0, "failures": 0},
                            "actions_used": {}}]
        }
    }, "")
    result = _get_combat_conditions()
    assert pc_id in result
    assert result[pc_id][0]["name"] == "Stunned"


# -- UI integration tests ----------------------------------------------------

def test_party_overview_renders_table(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    db.create_entity("adventurer", "Aldric", {"sheet": {"hp_current": 30, "hp_max": 40}}, "")

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(160, 40)) as pilot:
            await pilot.pause()
            await pilot.press("p")
            await pilot.pause()
            from screens.party_overview import PartyOverviewScreen
            assert isinstance(app.screen, PartyOverviewScreen)
            table = app.screen.query_one("#party-table")
            assert table is not None

    run(scenario)


def test_party_overview_shows_no_adventurers_message(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(160, 40)) as pilot:
            await pilot.pause()
            await pilot.press("p")
            await pilot.pause()
            status = app.screen.query_one("#overview-status").content
            assert "No active" in str(status)

    run(scenario)


def test_party_overview_excludes_dead_adventurers(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    db.create_entity("adventurer", "Live One", {"status": "Active"}, "")
    db.create_entity("adventurer", "Dead Hero", {"status": "Dead"}, "")

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(160, 40)) as pilot:
            await pilot.pause()
            await pilot.press("p")
            await pilot.pause()
            table = app.screen.query_one("#party-table")
            # DataTable rows count = number of adventurers shown
            assert table.row_count == 1

    run(scenario)
