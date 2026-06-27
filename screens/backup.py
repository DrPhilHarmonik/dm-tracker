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
from importers import import_entity
from importers.ddb import parse_ddb_json
from importers.csv_import import parse_csv, write_template
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
            Horizontal(
                Button("Export", id="btn-export", variant="success"),
                Button("Cancel", id="btn-cancel"),
                id="export-actions",
            ),
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
                Static("Import D&D Beyond Character", id="ddb-import-title"),
                Label("D&D Beyond character JSON export path:"),
                Input(value=str(Path.home() / "Downloads" / "character.json"), id="ddb-import-path"),
                Button("Import D&D Beyond Character", id="btn-ddb-import", variant="primary"),
                Static("", id="ddb-import-status"),
                Static("Import CSV", id="csv-import-title"),
                Label("CSV file path:"),
                Input(value=str(Path.home() / "campaign_import.csv"), id="csv-import-path"),
                Horizontal(
                    Button("Import CSV", id="btn-csv-import", variant="primary"),
                    Button("Download Template", id="btn-csv-template"),
                    id="csv-import-actions",
                ),
                Static("", id="csv-import-status"),
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
        elif event.button.id == "btn-ddb-import":
            self._do_ddb_import()
        elif event.button.id == "btn-csv-import":
            self._do_csv_import()
        elif event.button.id == "btn-csv-template":
            self._do_csv_template()
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

    def _do_ddb_import(self):
        path = Path(self.query_one("#ddb-import-path", Input).value.strip()).expanduser()
        status = self.query_one("#ddb-import-status", Static)
        try:
            parsed = parse_ddb_json(path)
            result = import_entity(
                parsed["name"], parsed["entity_type"],
                parsed["fields"], parsed["notes"],
            )
            msg = f"[green]Imported '{parsed['name']}' as adventurer[/green]"
            if result["warning"]:
                msg += f"\n[yellow]Warning: {result['warning']}[/yellow]"
            status.update(msg)
        except ValueError as ex:
            status.update(f"[red]{ex}[/red]")
        except Exception as ex:
            status.update(f"[red]{format_io_error(ex)}[/red]")

    def _do_csv_import(self):
        path = Path(self.query_one("#csv-import-path", Input).value.strip()).expanduser()
        status = self.query_one("#csv-import-status", Static)
        try:
            rows = parse_csv(path)
            if not rows:
                status.update("[yellow]No valid rows found -- check that 'name' and 'type' columns are present[/yellow]")
                return
            created = 0
            warnings = []
            for row in rows:
                result = import_entity(row["name"], row["entity_type"], row["fields"], row["notes"])
                created += 1
                if result["warning"]:
                    warnings.append(result["warning"])
            msg = f"[green]Imported {created} entity/entities[/green]"
            if warnings:
                msg += "\n[yellow]" + "; ".join(warnings) + "[/yellow]"
            status.update(msg)
        except Exception as ex:
            status.update(f"[red]{format_io_error(ex)}[/red]")

    def _do_csv_template(self):
        path = Path(self.query_one("#csv-import-path", Input).value.strip()).expanduser()
        template_path = path.parent / "campaign_import_template.csv"
        status = self.query_one("#csv-import-status", Static)
        try:
            write_template(template_path)
            status.update(f"[green]Template written to {template_path}[/green]")
        except Exception as ex:
            status.update(f"[red]{format_io_error(ex)}[/red]")
