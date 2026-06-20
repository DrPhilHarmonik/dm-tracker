"""UI interaction tests confirming the Export and Backup/Restore screens'
status messages actually update on both success and failure, through the
real button-press handlers rather than calling export.py directly.
"""
import asyncio

import db
from app import DMApp


def run(scenario):
    asyncio.run(scenario())


def test_export_screen_shows_success_status(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    db.create_entity("npc", "Gareth the Merchant", {}, "")

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            app.screen.action_export()
            await pilot.pause()
            export_screen = app.screen
            export_screen.query_one("#export-path").value = str(tmp_path / "vault")
            export_screen.query_one("#btn-export").press()
            await pilot.pause()
            status = str(export_screen.query_one("#export-status").content)
            assert "Exported 1 entities" in status
            assert (tmp_path / "vault" / "NPC" / "Gareth the Merchant.md").exists()

    run(scenario)


def test_export_screen_shows_categorized_error_on_failure(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            app.screen.action_export()
            await pilot.pause()
            export_screen = app.screen
            # a path through an existing *file* can't be mkdir'd as a directory
            blocking_file = tmp_path / "blocker"
            blocking_file.write_text("x")
            export_screen.query_one("#export-path").value = str(blocking_file / "vault")
            export_screen.query_one("#btn-export").press()
            await pilot.pause()
            status = str(export_screen.query_one("#export-status").content)
            assert "Expected a directory but found a file" in status

    run(scenario)


def test_backup_screen_shows_success_status_for_json_backup(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    db.create_entity("npc", "Gareth the Merchant", {}, "")

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            app.screen.action_backup()
            await pilot.pause()
            backup_screen = app.screen
            backup_screen.query_one("#backup-path").value = str(tmp_path / "backup.json")
            backup_screen.query_one("#btn-backup").press()
            await pilot.pause()
            status = str(backup_screen.query_one("#backup-status").content)
            assert "Backed up 1 entities" in status

    run(scenario)


def test_backup_screen_shows_path_not_found_for_missing_restore_file(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            app.screen.action_backup()
            await pilot.pause()
            backup_screen = app.screen
            backup_screen.query_one("#restore-path").value = str(tmp_path / "missing.json")
            backup_screen.query_one("#btn-restore").press()
            await pilot.pause()
            status = str(backup_screen.query_one("#restore-status").content)
            assert "Path not found" in status

    run(scenario)


def test_backup_screen_vault_import_replace_requires_confirmation(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    db.create_entity("npc", "Existing NPC", {}, "")

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            app.screen.action_backup()
            await pilot.pause()
            backup_screen = app.screen
            backup_screen.query_one("#vault-import-path").value = str(tmp_path / "nonexistent_vault")
            backup_screen.query_one("#btn-vault-import-replace").press()
            await pilot.pause()
            # confirmation dialog should be up, no import attempted yet
            assert "ConfirmScreen" in str(type(app.screen))
            await pilot.click("#btn-no")
            await pilot.pause()
            assert app.screen is backup_screen
            status = str(backup_screen.query_one("#vault-import-status").content)
            assert status == ""  # declined -- nothing attempted, no error shown

    run(scenario)
