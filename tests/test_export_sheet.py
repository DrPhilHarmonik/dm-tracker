import asyncio
from pathlib import Path

import db
import export as exp


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()


def _make_adventurer(name="Thorin") -> int:
    return db.create_entity(
        "adventurer",
        name,
        {
            "class_name": "Fighter",
            "level": "3",
            "sheet": {
                "level": 3,
                "hp_max": 28,
                "hp_current": 28,
                "ac": 16,
                "abilities": {"str": 16, "dex": 12, "con": 14, "int": 10, "wis": 11, "cha": 9},
            },
        },
        "",
    )


def _make_enemy(name="Goblin Boss") -> int:
    return db.create_entity(
        "enemy",
        name,
        {
            "cr": "1",
            "creature_type": "Humanoid",
            "sheet": {
                "cr": "1",
                "creature_type": "Humanoid",
                "hp_max": 21,
                "hp_current": 21,
                "ac": 17,
                "abilities": {"str": 10, "dex": 14, "con": 10, "int": 10, "wis": 8, "cha": 8},
            },
        },
        "",
    )


def test_export_creates_file(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = _make_adventurer()
    out = tmp_path / "exports" / "thorin_sheet.md"
    path = exp.export_entity_sheet(eid, out)
    assert path == out
    assert path.exists()


def test_export_contains_entity_name(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = _make_adventurer("Brynn")
    out = tmp_path / "brynn.md"
    exp.export_entity_sheet(eid, out)
    content = out.read_text()
    assert "Brynn" in content


def test_export_contains_sheet_section(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = _make_adventurer()
    out = tmp_path / "sheet.md"
    exp.export_entity_sheet(eid, out)
    content = out.read_text()
    assert "## Character Sheet" in content


def test_export_contains_abilities(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = _make_adventurer()
    out = tmp_path / "abilities.md"
    exp.export_entity_sheet(eid, out)
    content = out.read_text()
    assert "STR" in content
    assert "DEX" in content


def test_export_enemy_contains_cr(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = _make_enemy()
    out = tmp_path / "enemy.md"
    exp.export_entity_sheet(eid, out)
    content = out.read_text()
    assert "CR" in content


def test_export_default_path_slugified_name(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = _make_adventurer("Zara the Bold")
    out = tmp_path / "zara-the-bold_sheet.md"
    path = exp.export_entity_sheet(eid, out)
    assert path.exists()
    assert "Zara the Bold" in path.read_text()


def test_export_missing_entity_raises(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    import pytest
    with pytest.raises(ValueError, match="not found"):
        exp.export_entity_sheet(9999, tmp_path / "out.md")


def test_export_creates_parent_dirs(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = _make_adventurer()
    deep = tmp_path / "a" / "b" / "c" / "sheet.md"
    exp.export_entity_sheet(eid, deep)
    assert deep.exists()


# -- UI smoke test --

def run(scenario):
    asyncio.run(scenario())


def test_ui_export_sheet_button_exists(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = _make_adventurer("Petra")

    async def scenario():
        from app import DMApp
        from screens.sheet import CharacterSheetScreen
        app = DMApp()
        async with app.run_test(size=(180, 50)) as pilot:
            await pilot.pause()
            app.push_screen(CharacterSheetScreen(eid))
            for _ in range(8):
                await pilot.pause()
            assert isinstance(app.screen, CharacterSheetScreen)
            btn = app.screen.query_one("#btn-export-sheet")
            assert btn is not None

    run(scenario)
