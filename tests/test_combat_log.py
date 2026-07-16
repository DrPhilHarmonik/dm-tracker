import combat as cbt


def test_default_combat_has_log():
    c = cbt.default_combat()
    assert "log" in c
    assert c["log"] == []


def test_normalize_combat_preserves_log():
    raw = {"round": 2, "log": [{"round": 1, "entry": "started"}]}
    c = cbt.normalize_combat(raw)
    assert c["log"] == [{"round": 1, "entry": "started"}]


def test_normalize_combat_missing_log_defaults_empty():
    c = cbt.normalize_combat({"round": 1})
    assert c["log"] == []


def test_log_entry_appends():
    c = cbt.default_combat()
    c = cbt.log_entry(c, 1, "Encounter started")
    assert len(c["log"]) == 1
    assert c["log"][0] == {"round": 1, "entry": "Encounter started"}


def test_log_entry_multiple():
    c = cbt.default_combat()
    c = cbt.log_entry(c, 1, "first")
    c = cbt.log_entry(c, 1, "second")
    c = cbt.log_entry(c, 2, "third")
    assert len(c["log"]) == 3
    assert c["log"][2]["round"] == 2


def test_log_entry_does_not_mutate_unrelated_fields():
    c = cbt.default_combat()
    c["round"] = 3
    c = cbt.log_entry(c, 3, "test")
    assert c["round"] == 3
    assert len(c["log"]) == 1


def test_log_survives_normalize_roundtrip():
    c = cbt.default_combat()
    c = cbt.log_entry(c, 1, "hello")
    c2 = cbt.normalize_combat(c)
    assert c2["log"] == [{"round": 1, "entry": "hello"}]
