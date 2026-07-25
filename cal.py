CALENDARS: dict[str, dict] = {
    "gregorian": {
        "name": "Gregorian",
        "months": [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ],
        "days_per_month": [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31],
        "intercalary": [],
    },
    "harptos": {
        "name": "Calendar of Harptos",
        "months": [
            "Hammer", "Alturiak", "Ches", "Tarsakh", "Mirtul", "Kythorn",
            "Flamerule", "Eleasis", "Eleint", "Marpenoth", "Uktar", "Nightal",
        ],
        "days_per_month": [30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30],
        "intercalary": [
            "Midwinter",
            "Greengrass",
            "Midsummer",
            "Highharvestide",
            "Feast of the Moon",
        ],
    },
}

DEFAULT_CALENDAR = "gregorian"


def calendar_names() -> list[str]:
    return list(CALENDARS.keys())


def month_names(calendar_key: str = DEFAULT_CALENDAR) -> list[str]:
    cal = CALENDARS.get(calendar_key) or CALENDARS[DEFAULT_CALENDAR]
    return list(cal["months"])


def intercalary_days(calendar_key: str = DEFAULT_CALENDAR) -> list[str]:
    cal = CALENDARS.get(calendar_key) or CALENDARS[DEFAULT_CALENDAR]
    return list(cal.get("intercalary", []))


def sort_sessions(sessions: list[dict]) -> list[dict]:
    """Sort sessions by session_number ascending; sessions without one sort last, then by id."""
    def _key(s: dict) -> tuple:
        try:
            num = int(s["fields"].get("session_number") or 0)
            if num <= 0:
                return (float("inf"), s["id"])
            return (num, s["id"])
        except (TypeError, ValueError):
            return (float("inf"), s["id"])
    return sorted(sessions, key=_key)
