"""Tests for Phase 31 -- Level-Up Workflow (levelup.py)."""
import pytest
import levelup as lvu
import sheet as shm
import classes as cls_mod


# ---------------------------------------------------------------------------
# average_hp_gain
# ---------------------------------------------------------------------------

def test_average_hp_gain_fighter():
    # Fighter d10: 10//2 + 1 + CON_mod
    assert lvu.average_hp_gain("Fighter", 0) == 6      # 5 + 1 + 0
    assert lvu.average_hp_gain("Fighter", 2) == 8      # 5 + 1 + 2
    assert lvu.average_hp_gain("Fighter", -1) == 5     # 5 + 1 - 1


def test_average_hp_gain_barbarian():
    # Barbarian d12: 6 + 1 + CON_mod = 7 base
    assert lvu.average_hp_gain("Barbarian", 0) == 7
    assert lvu.average_hp_gain("Barbarian", 3) == 10


def test_average_hp_gain_wizard():
    # Wizard d6: 3 + 1 + CON_mod = 4 base
    assert lvu.average_hp_gain("Wizard", 0) == 4
    assert lvu.average_hp_gain("Wizard", -1) == 3


def test_average_hp_gain_minimum_one():
    # Even with a very negative CON modifier the minimum is 1
    assert lvu.average_hp_gain("Wizard", -10) == 1


def test_average_hp_gain_unknown_class():
    # Unknown class falls back to d8 (default)
    assert lvu.average_hp_gain("", 0) == 5    # 4 + 1 + 0


# ---------------------------------------------------------------------------
# slot_table
# ---------------------------------------------------------------------------

def test_slot_table_full_caster():
    for cls in ("Bard", "Cleric", "Druid", "Sorcerer", "Wizard"):
        table = lvu.slot_table(cls)
        assert table is not None
        # Level 1 full caster has 2 first-level slots
        assert table[1][1] == 2
        # Level 20 has 4 first-level slots and second-level 9th-level slots
        assert table[20][1] == 4
        assert table[20][9] == 1


def test_slot_table_half_caster():
    for cls in ("Paladin", "Ranger"):
        table = lvu.slot_table(cls)
        # Half casters get no slots at level 1
        assert 1 not in table
        # Level 2 gives first slot
        assert table[2][1] == 2


def test_slot_table_warlock():
    table = lvu.slot_table("Warlock")
    # Level 1: 1 first-level slot
    assert table[1][1] == 1
    # Level 3: switches to 2nd-level
    assert table[3][2] == 2
    assert 1 not in table[3]


def test_slot_table_non_caster():
    for cls in ("Fighter", "Barbarian", "Monk", "Rogue"):
        assert lvu.slot_table(cls) == {}


# ---------------------------------------------------------------------------
# features_at_level
# ---------------------------------------------------------------------------

def test_features_at_level_known():
    # All classes should have entry for level 4 (ASI)
    for cls in cls_mod.CLASS_HIT_DICE:
        feat = lvu.features_at_level(cls, 4)
        assert isinstance(feat, str)


def test_features_at_level_unknown_class():
    assert lvu.features_at_level("HomebewClass", 5) == ""


def test_features_at_level_level_1_absent():
    # Level 1 features are applied at character creation, not level-up
    assert lvu.features_at_level("Fighter", 1) == ""


# ---------------------------------------------------------------------------
# apply_level_up -- non-caster
# ---------------------------------------------------------------------------

@pytest.fixture
def fighter_sheet():
    return shm.normalize_sheet({
        "level": 4,
        "hp_max": 40,
        "hp_current": 30,
        "abilities": {"str": 16, "dex": 12, "con": 14, "int": 10, "wis": 10, "cha": 8},
    })


def test_apply_level_up_increments_level(fighter_sheet):
    result = lvu.apply_level_up(fighter_sheet, "Fighter", 8)
    assert result["level"] == 5


def test_apply_level_up_adds_hp(fighter_sheet):
    result = lvu.apply_level_up(fighter_sheet, "Fighter", 8)
    assert result["hp_max"] == 48


def test_apply_level_up_minimum_hp_gain(fighter_sheet):
    result = lvu.apply_level_up(fighter_sheet, "Fighter", 1)
    assert result["hp_max"] == 41


def test_apply_level_up_updates_hit_dice(fighter_sheet):
    result = lvu.apply_level_up(fighter_sheet, "Fighter", 6)
    assert result["hit_dice"] == "5d10"


def test_apply_level_up_no_slots_for_fighter(fighter_sheet):
    result = lvu.apply_level_up(fighter_sheet, "Fighter", 6)
    # No spell slots -- all should remain 0
    for lvl in range(1, 10):
        assert result["spell_slots"][str(lvl)]["max"] == 0


# ---------------------------------------------------------------------------
# apply_level_up -- full caster (Wizard level 2 -> 3)
# ---------------------------------------------------------------------------

@pytest.fixture
def wizard_sheet():
    return shm.normalize_sheet({
        "level": 2,
        "hp_max": 12,
        "abilities": {"str": 8, "dex": 14, "con": 12, "int": 18, "wis": 10, "cha": 10},
        "spell_slots": {
            "1": {"current": 3, "max": 3},
            "2": {"current": 0, "max": 0},
        },
    })


def test_apply_level_up_wizard_slot_increase(wizard_sheet):
    # Wizard 2 has {1: 3}; Wizard 3 has {1: 4, 2: 2}
    result = lvu.apply_level_up(wizard_sheet, "Wizard", 4)
    assert result["spell_slots"]["1"]["max"] == 4
    assert result["spell_slots"]["2"]["max"] == 2


def test_apply_level_up_wizard_current_tracks_delta(wizard_sheet):
    # current was 3/3; after level-up: max increases by 1 → current should become 4
    result = lvu.apply_level_up(wizard_sheet, "Wizard", 4)
    assert result["spell_slots"]["1"]["current"] == 4
    # New 2nd-level slots: delta=2, current=0+2=2
    assert result["spell_slots"]["2"]["current"] == 2


def test_apply_level_up_current_does_not_exceed_max(wizard_sheet):
    # If current was already at max, current == max after gain
    wizard_sheet["spell_slots"]["1"]["current"] = 3
    result = lvu.apply_level_up(wizard_sheet, "Wizard", 4)
    assert result["spell_slots"]["1"]["current"] <= result["spell_slots"]["1"]["max"]


# ---------------------------------------------------------------------------
# apply_level_up -- half caster (Paladin level 1 -> 2, gains first slots)
# ---------------------------------------------------------------------------

def test_apply_level_up_paladin_gains_first_slots():
    sheet = shm.normalize_sheet({"level": 1, "hp_max": 12})
    result = lvu.apply_level_up(sheet, "Paladin", 7)
    assert result["spell_slots"]["1"]["max"] == 2


def test_apply_level_up_paladin_level_1_no_slots():
    # Paladin has no slots at level 1 -- verify old_max is correctly 0
    sheet = shm.normalize_sheet({"level": 1, "hp_max": 12})
    assert sheet["spell_slots"]["1"]["max"] == 0


# ---------------------------------------------------------------------------
# apply_level_up -- Warlock pact magic
# ---------------------------------------------------------------------------

def test_apply_level_up_warlock_2_to_3():
    # Warlock 2: {1: 2}; Warlock 3: {2: 2} -- slot level changes!
    sheet = shm.normalize_sheet({
        "level": 2,
        "hp_max": 14,
        "spell_slots": {"1": {"current": 2, "max": 2}},
    })
    result = lvu.apply_level_up(sheet, "Warlock", 5)
    assert result["spell_slots"]["2"]["max"] == 2
    # Level-1 slots drop to 0 (Warlock no longer has them at level 3)
    assert result["spell_slots"]["1"]["max"] == 0


# ---------------------------------------------------------------------------
# apply_level_up -- level cap
# ---------------------------------------------------------------------------

def test_apply_level_up_caps_at_20():
    sheet = shm.normalize_sheet({"level": 20, "hp_max": 200})
    result = lvu.apply_level_up(sheet, "Fighter", 10)
    assert result["level"] == 20


# ---------------------------------------------------------------------------
# DB integration
# ---------------------------------------------------------------------------

@pytest.fixture
def adv_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "test.db"))
    import db
    db.init_db()
    adv_id = db.create_entity(
        "adventurer",
        "Gorrak",
        {
            "class_name": "Fighter",
            "xp": 900,
            "level": "4",
            "sheet": {
                "level": 4,
                "hp_max": 40,
                "hp_current": 40,
                "abilities": {"str": 16, "dex": 12, "con": 14, "int": 10, "wis": 10, "cha": 8},
            },
        },
        "",
    )
    return adv_id


def test_apply_level_up_persists_to_db(adv_db):
    import db
    entity = db.get_entity(adv_db)
    fields = dict(entity["fields"])
    class_name = fields.get("class_name", "")
    new_sheet = lvu.apply_level_up(fields.get("sheet", {}), class_name, 8)
    fields["sheet"] = new_sheet
    fields["level"] = str(new_sheet["level"])
    db.update_entity(adv_db, entity["name"], fields, entity["notes"])

    reloaded = db.get_entity(adv_db)
    assert reloaded["fields"]["sheet"]["level"] == 5
    assert reloaded["fields"]["sheet"]["hp_max"] == 48
    assert reloaded["fields"]["level"] == "5"
