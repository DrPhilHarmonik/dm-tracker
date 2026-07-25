import cal


def test_gregorian_has_12_months():
    assert len(cal.month_names("gregorian")) == 12


def test_gregorian_month_names():
    months = cal.month_names("gregorian")
    assert months[0] == "January"
    assert months[11] == "December"


def test_harptos_has_12_months():
    assert len(cal.month_names("harptos")) == 12


def test_harptos_month_names():
    months = cal.month_names("harptos")
    assert months[0] == "Hammer"
    assert months[11] == "Nightal"


def test_harptos_intercalary_days():
    days = cal.intercalary_days("harptos")
    assert "Midwinter" in days
    assert "Midsummer" in days
    assert len(days) == 5


def test_gregorian_no_intercalary():
    assert cal.intercalary_days("gregorian") == []


def test_unknown_calendar_falls_back_to_gregorian():
    assert cal.month_names("nonexistent") == cal.month_names("gregorian")
    assert cal.intercalary_days("nonexistent") == cal.intercalary_days("gregorian")


def test_calendar_names_includes_presets():
    names = cal.calendar_names()
    assert "gregorian" in names
    assert "harptos" in names


def test_default_calendar_is_gregorian():
    assert cal.DEFAULT_CALENDAR == "gregorian"


def test_sort_sessions_by_number():
    sessions = [
        {"id": 3, "fields": {"session_number": 3}},
        {"id": 1, "fields": {"session_number": 1}},
        {"id": 2, "fields": {"session_number": 2}},
    ]
    result = cal.sort_sessions(sessions)
    assert [s["id"] for s in result] == [1, 2, 3]


def test_sort_sessions_missing_number_last():
    sessions = [
        {"id": 2, "fields": {"session_number": 2}},
        {"id": 99, "fields": {}},
        {"id": 1, "fields": {"session_number": 1}},
    ]
    result = cal.sort_sessions(sessions)
    assert result[0]["id"] == 1
    assert result[1]["id"] == 2
    assert result[2]["id"] == 99


def test_sort_sessions_zero_number_treated_as_no_number():
    sessions = [
        {"id": 5, "fields": {"session_number": 0}},
        {"id": 1, "fields": {"session_number": 1}},
    ]
    result = cal.sort_sessions(sessions)
    assert result[0]["id"] == 1
    assert result[1]["id"] == 5


def test_sort_sessions_tie_broken_by_id():
    sessions = [
        {"id": 10, "fields": {"session_number": 1}},
        {"id": 2, "fields": {"session_number": 1}},
    ]
    result = cal.sort_sessions(sessions)
    assert [s["id"] for s in result] == [2, 10]


def test_sort_sessions_empty():
    assert cal.sort_sessions([]) == []


def test_sort_sessions_single():
    s = [{"id": 1, "fields": {"session_number": 5}}]
    assert cal.sort_sessions(s) == s
