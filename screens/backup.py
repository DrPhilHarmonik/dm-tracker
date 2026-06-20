from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Label, Button, DataTable, Input, Select, TextArea, Static, ListView, ListItem, TabbedContent, TabPane, Switch
from textual.screen import Screen, ModalScreen
from textual.containers import Container, Horizontal, ScrollableContainer
from textual import on
from rich.text import Text
from pathlib import Path

import db
import export as exp
import sheet as shm
import dice
import combat as cbt
import effects as fx
import classes
from models import ENTITY_TYPES, ENTITY_LABELS, ENTITY_LABELS_PLURAL, ENTITY_SCHEMAS, RELATIONSHIP_TYPES

from screens.common import DismissableScreen, PALETTE, format_io_error
from screens.modals import ConfirmScreen

class ExportScreen(DismissableScreen):
    BINDINGS = [Binding("escape", "dismiss_screen", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("Export Campaign to Obsidian Vault", id="export-title"),
            Label("Output directory:"),
            Input(value=str(Path.home() / "campaign_vault"), id="export-path"),
            Horizontal(
                Switch(value=True, id="export-include-stats"),
                Label("Include character sheets & active effects"),
                id="export-stats-row",
            ),
            Button("Export", id="btn-export", variant="success"),
            Button("Cancel", id="btn-cancel"),
            Static("", id="export-status"),
            id="export-container",
        )
        yield Footer()

    def on_mount(self):
        self.title = "Export to Markdown"

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-export":
            path_str = self.query_one("#export-path", Input).value.strip()
            out_path = Path(path_str).expanduser()
            include_stats = self.query_one("#export-include-stats", Switch).value
            try:
                count = exp.export_vault(out_path, include_stats=include_stats)
                self.query_one("#export-status", Static).update(
                    f"[green]Exported {count} entities to {out_path}[/green]"
                )
            except Exception as ex:
                self.query_one("#export-status", Static).update(f"[red]{format_io_error(ex)}[/red]")
        elif event.button.id == "btn-cancel":
            self.dismiss()


# ---------------------------------------------------------------------------
# Backup / Restore
# ---------------------------------------------------------------------------

class BackupScreen(DismissableScreen):
    BINDINGS = [Binding("escape", "dismiss_screen", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(
            Container(
                Static("Backup & Restore (JSON)", id="backup-title"),
                Label("Backup file path:"),
                Input(value=str(Path.home() / "campaign_backup.json"), id="backup-path"),
                Button("Backup Now", id="btn-backup", variant="success"),
                Static("", id="backup-status"),
                Label("Restore file path:"),
                Input(value=str(Path.home() / "campaign_backup.json"), id="restore-path"),
                Horizontal(
                    Button("Restore (into empty DB)", id="btn-restore", variant="primary"),
                    Button("Restore & Replace All Data", id="btn-restore-replace", variant="error"),
                ),
                Static("", id="restore-status"),
                Static("Import Markdown Vault", id="vault-import-title"),
                Label("Vault directory (must have been exported by this app):"),
                Input(value=str(Path.home() / "campaign_vault"), id="vault-import-path"),
                Horizontal(
                    Button("Import (into empty DB)", id="btn-vault-import", variant="primary"),
                    Button("Import & Replace All Data", id="btn-vault-import-replace", variant="error"),
                ),
                Static("", id="vault-import-status"),
                Button("Back", id="btn-back"),
                id="backup-container",
            ),
            id="backup-scroll",
        )
        yield Footer()

    def on_mount(self):
        self.title = "Backup & Restore"

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-backup":
            self._do_backup()
        elif event.button.id == "btn-restore":
            self._do_restore(replace=False)
        elif event.button.id == "btn-restore-replace":
            self.app.push_screen(
                ConfirmScreen("This will ERASE all current data and replace it with the backup. Continue?"),
                callback=self._on_replace_confirmed,
            )
        elif event.button.id == "btn-vault-import":
            self._do_vault_import(replace=False)
        elif event.button.id == "btn-vault-import-replace":
            self.app.push_screen(
                ConfirmScreen("This will ERASE all current data and replace it with the imported vault. Continue?"),
                callback=self._on_vault_replace_confirmed,
            )
        elif event.button.id == "btn-back":
            self.dismiss()

    def _on_replace_confirmed(self, confirmed: bool):
        if confirmed:
            self._do_restore(replace=True)

    def _on_vault_replace_confirmed(self, confirmed: bool):
        if confirmed:
            self._do_vault_import(replace=True)

    def _do_backup(self):
        path = Path(self.query_one("#backup-path", Input).value.strip()).expanduser()
        try:
            count = exp.export_json_backup(path)
            self.query_one("#backup-status", Static).update(f"[green]Backed up {count} entities to {path}[/green]")
        except Exception as ex:
            self.query_one("#backup-status", Static).update(f"[red]{format_io_error(ex)}[/red]")

    def _do_restore(self, replace: bool):
        path = Path(self.query_one("#restore-path", Input).value.strip()).expanduser()
        try:
            result = exp.import_json_backup(path, replace=replace)
            self.query_one("#restore-status", Static).update(
                f"[green]Restored {result['entities']} entities and {result['relationships']} relationships[/green]"
            )
        except Exception as ex:
            self.query_one("#restore-status", Static).update(f"[red]{format_io_error(ex)}[/red]")

    def _do_vault_import(self, replace: bool):
        path = Path(self.query_one("#vault-import-path", Input).value.strip()).expanduser()
        try:
            result = exp.import_vault(path, replace=replace)
            self.query_one("#vault-import-status", Static).update(
                f"[green]Imported {result['entities']} entities and {result['relationships']} relationships[/green]"
            )
        except Exception as ex:
            self.query_one("#vault-import-status", Static).update(f"[red]{format_io_error(ex)}[/red]")
