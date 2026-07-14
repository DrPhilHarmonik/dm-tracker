import rest
import sheet as shm


def _sheet(hp_current=20, hp_max=30, con=14, hit_dice="4d8+8", class_name="Cleric", level=4,
           spell_slots=None):
    s = shm.normalize_sheet({
        "abilities": {"str": 10, "dex": 10, "con": con, "int": 10, "wis": 16, "cha": 10},
        "hp_current": hp_current, "hp_max": hp_max, "hit_dice": hit_dice,
        "class_name": class_name, "level": level,
        "spellcasting_ability": "wis",
        "spell_slots": spell_slots or {"1": {"current": 2, "max": 4}, "2": {"current": 0, "max": 3},
                                       **{str(i): {"current": 0, "max": 0} for i in range(3, 10)}},
    })
    return s


def test_roll_hit_dice_zero_returns_zero():
    gain, detail = rest.roll_hit_dice(_sheet(), 0)
    assert gain == 0


def test_roll_hit_dice_positive_count(monkeypatch):
    # Monkeypatch dice.roll to always return 5 so we get deterministic results
    import dice
    class FakeResult:
        total = 5
    monkeypatch.setattr(dice, "roll", lambda expr, rng=None: FakeResult())
    s = _sheet(con=14)  # CON +2
    gain, detail = rest.roll_hit_dice(s, 2)
    # Each die: 5 + 2 = 7; total = 14
    assert gain == 14
    assert "14" in detail


def test_roll_hit_dice_never_below_one_per_die(monkeypatch):
    import dice
    class FakeResult:
        total = 1
    monkeypatch.setattr(dice, "roll", lambda expr, rng=None: FakeResult())
    s = _sheet(con=1)   # CON -5; each die still floors at 1
    gain, _ = rest.roll_hit_dice(s, 3)
    assert gain >= 3     # at least 1 per die


def test_apply_short_rest_adds_hp():
    s = _sheet(hp_current=10, hp_max=30)
    result = rest.apply_short_rest(s, 8)
    assert result["hp_current"] == 18


def test_apply_short_rest_clamps_at_max():
    s = _sheet(hp_current=28, hp_max=30)
    result = rest.apply_short_rest(s, 10)
    assert result["hp_current"] == 30


def test_apply_short_rest_does_not_mutate_original():
    s = _sheet(hp_current=10, hp_max=30)
    rest.apply_short_rest(s, 5)
    assert s["hp_current"] == 10


def test_apply_long_rest_restores_hp():
    s = _sheet(hp_current=5, hp_max=30)
    result = rest.apply_long_rest(s)
    assert result["hp_current"] == 30


def test_apply_long_rest_restores_spell_slots():
    s = _sheet(spell_slots={"1": {"current": 1, "max": 4},
                             "2": {"current": 0, "max": 3},
                             **{str(i): {"current": 0, "max": 0} for i in range(3, 10)}})
    result = rest.apply_long_rest(s)
    assert result["spell_slots"]["1"]["current"] == 4
    assert result["spell_slots"]["2"]["current"] == 3


def test_apply_long_rest_does_not_mutate_original():
    s = _sheet(hp_current=5, hp_max=30)
    rest.apply_long_rest(s)
    assert s["hp_current"] == 5


def test_hit_die_sides_from_class_name():
    # class_name lives outside the normalized sheet; pass it directly
    s = rest.shm.normalize_sheet({"hit_dice": "4d8+8"})
    s["class_name"] = "Fighter"
    assert rest._hit_die_sides(s) == 10  # Fighter = d10


def test_hit_die_sides_fallback_to_notation():
    s = _sheet(class_name="UnknownClass", hit_dice="6d12+18")
    assert rest._hit_die_sides(s) == 12


def test_active_adventurers_excludes_dead(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    import db; db.init_db()
    db.create_entity("adventurer", "Alive Hero", {"status": "Active"}, "")
    db.create_entity("adventurer", "Dead Hero", {"status": "Dead"}, "")
    db.create_entity("adventurer", "Retired Hero", {"status": "Retired"}, "")
    result = rest.active_adventurers()
    names = [e["name"] for e in result]
    assert "Alive Hero" in names
    assert "Dead Hero" not in names
    assert "Retired Hero" not in names
