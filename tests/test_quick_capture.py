"""Tests for the Quick Capture overlay and the db.latest_session() helper."""
import asyncio
import pytest
import db
from app import DMApp


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "test.db"))
    db.init_db()


# --- db.latest_session() unit tests ---

def test_latest_session_returns_none_when_no_sessions():
    assert db.latest_session() is None


def test_latest_session_returns_most_recent():
    db.create_entity("session", "Session 1", {}, "")
    db.create_entity("session", "Session 2", {}, "")
    result = db.latest_session()
    assert result is not None
    assert result["name"] == "Session 2"


def test_latest_session_not_affected_by_other_types():
    db.create_entity("npc", "Bob", {}, "")
    assert db.latest_session() is None


# --- _append_note unit tests ---

def test_append_note_adds_to_empty_notes():
    from screens.quick_capture import _append_note
    eid = db.create_entity("npc", "Mira", {}, "")
    _append_note(eid, "She smiled.")
    entity = db.get_entity(eid)
    assert entity["notes"] == "She smiled."


def test_append_note_separates_with_blank_line():
    from screens.quick_capture import _append_note
    eid = db.create_entity("npc", "Gareth", {}, "Old note.")
    _append_note(eid, "New note.")
    entity = db.get_entity(eid)
    assert entity["notes"] == "Old note.\n\nNew note."


def test_append_note_noop_for_missing_entity():
    from screens.quick_capture import _append_note
    _append_note(9999, "Ghost note.")  # should not raise


# --- QuickCaptureModal UI tests ---

async def _run(coro):
    return await coro


def test_modal_saves_to_session(tmp_path):
    session_id = db.create_entity("session", "Game Night", {}, "")

    async def run():
        app = DMApp()
        async with app.run_test(size=(140, 50)) as pilot:
            await pilot.pause()
            from screens.quick_capture import QuickCaptureModal
            modal = QuickCaptureModal(session_id, round_number=None)
            app.push_screen(modal)
            await pilot.pause()
            modal.query_one("#qc-note").value = "The dragon appeared."
            modal._do_save()
            await pilot.pause()

    asyncio.run(run())
    entity = db.get_entity(session_id)
    assert "The dragon appeared." in entity["notes"]


def test_modal_prefixes_round_number(tmp_path):
    session_id = db.create_entity("session", "Battle", {}, "")

    async def run():
        app = DMApp()
        async with app.run_test(size=(140, 50)) as pilot:
            await pilot.pause()
            from screens.quick_capture import QuickCaptureModal
            modal = QuickCaptureModal(session_id, round_number=3)
            app.push_screen(modal)
            await pilot.pause()
            modal.query_one("#qc-note").value = "Hero falls."
            modal._do_save()
            await pilot.pause()

    asyncio.run(run())
    entity = db.get_entity(session_id)
    assert "[Round 3] Hero falls." in entity["notes"]


def test_modal_also_tags_entity(tmp_path):
    session_id = db.create_entity("session", "Session A", {}, "")
    npc_id = db.create_entity("npc", "Lord Varis", {}, "")

    async def run():
        app = DMApp()
        async with app.run_test(size=(140, 50)) as pilot:
            await pilot.pause()
            from screens.quick_capture import QuickCaptureModal
            modal = QuickCaptureModal(session_id, round_number=None)
            app.push_screen(modal)
            await pilot.pause()
            modal.query_one("#qc-note").value = "He offered a deal."
            # Manually set filtered entities to simulate tag selection
            modal._filtered_entities = [db.get_entity(npc_id)]
            modal.query_one("#qc-entity-list").display = True
            modal._do_save()
            await pilot.pause()

    asyncio.run(run())
    session = db.get_entity(session_id)
    npc = db.get_entity(npc_id)
    assert "He offered a deal." in session["notes"]
    assert "He offered a deal." in npc["notes"]


def test_modal_no_session_requires_tag(tmp_path):
    """Without a session and no selected entity, save should set error status."""
    async def run():
        app = DMApp()
        async with app.run_test(size=(140, 50)) as pilot:
            await pilot.pause()
            from screens.quick_capture import QuickCaptureModal
            modal = QuickCaptureModal(None, round_number=None)
            app.push_screen(modal)
            await pilot.pause()
            modal.query_one("#qc-note").value = "Orphaned note."
            modal._do_save()
            await pilot.pause()
            status = modal.query_one("#qc-status").content
            assert "session" in status.lower()

    asyncio.run(run())


def test_modal_empty_note_shows_error(tmp_path):
    session_id = db.create_entity("session", "S", {}, "")

    async def run():
        app = DMApp()
        async with app.run_test(size=(140, 50)) as pilot:
            await pilot.pause()
            from screens.quick_capture import QuickCaptureModal
            modal = QuickCaptureModal(session_id, None)
            app.push_screen(modal)
            await pilot.pause()
            modal._do_save()
            await pilot.pause()
            status = modal.query_one("#qc-status").content
            assert "empty" in status.lower()

    asyncio.run(run())


def test_app_quick_capture_resolves_latest_session():
    session_id = db.create_entity("session", "Latest Session", {}, "")

    async def run():
        app = DMApp()
        async with app.run_test(size=(140, 50)) as pilot:
            await pilot.pause()
            resolved = app._resolve_session()
            assert resolved == session_id

    asyncio.run(run())


def test_app_quick_capture_caches_session_id():
    session_id = db.create_entity("session", "Cached", {}, "")

    async def run():
        app = DMApp()
        async with app.run_test(size=(140, 50)) as pilot:
            await pilot.pause()
            app._resolve_session()
            assert app._active_session_id == session_id
            # A second call should reuse the cached ID
            resolved = app._resolve_session()
            assert resolved == session_id

    asyncio.run(run())


def test_get_combat_round_returns_none_when_no_combat():
    async def run():
        app = DMApp()
        async with app.run_test(size=(140, 50)) as pilot:
            await pilot.pause()
            assert app._get_combat_round() is None

    asyncio.run(run())
