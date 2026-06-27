from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Label, Button, DataTable, Input, Static
from textual.containers import Container, Horizontal, ScrollableContainer
from textual import on

import db
import campaign_manager as cm
from screens.common import DismissableScreen
from screens.modals import ConfirmScreen


class CampaignSwitcherScreen(DismissableScreen):
    BINDINGS = [Binding("escape", "dismiss_screen", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(
            Container(
                Static("Campaigns", id="campaign-title"),
                DataTable(id="campaign-table"),
                Horizontal(
                    Button("Open Selected", id="btn-campaign-open", variant="primary"),
                    Button("Rename Selected", id="btn-campaign-rename"),
                    Button("Delete Selected", id="btn-campaign-delete", variant="error"),
                    id="campaign-actions",
                ),
                Static("", id="campaign-status"),
                Static("New Campaign", id="new-campaign-title"),
                Label("Campaign name:"),
                Input(placeholder="My Campaign", id="input-campaign-name"),
                Button("Create Campaign", id="btn-campaign-create", variant="success"),
                id="campaign-container",
            ),
            id="campaign-scroll",
        )
        yield Footer()

    def on_mount(self):
        self.title = "Campaigns"
        table = self.query_one("#campaign-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("Name", "Last Opened", "Entities", "Path")
        self._refresh_table()

    def _refresh_table(self):
        table = self.query_one("#campaign-table", DataTable)
        table.clear()
        current_path = str(db.db_path().resolve())
        for campaign in cm.list_campaigns():
            is_active = str(campaign["path"]) == current_path
            name = f"[bold]{campaign['name']}[/bold] (active)" if is_active else campaign["name"]
            last = campaign["last_opened_at"][:10]
            count = str(cm.entity_count_for(campaign["path"]))
            path = campaign["path"]
            table.add_row(name, last, count, path, key=str(campaign["id"]))

    def _selected_campaign_id(self) -> int | None:
        table = self.query_one("#campaign-table", DataTable)
        if table.cursor_row < 0:
            return None
        row_key = table.get_row_at(table.cursor_row)
        # row_key is None when table is empty; use the row key we set
        key = table.coordinate_to_cell_key((table.cursor_row, 0)).row_key.value
        try:
            return int(key)
        except (TypeError, ValueError):
            return None

    def _open_selected(self):
        campaign_id = self._selected_campaign_id()
        if campaign_id is None:
            self.query_one("#campaign-status", Static).update("[yellow]Select a campaign first[/yellow]")
            return
        campaign = cm.get_campaign(campaign_id)
        if not campaign:
            return
        path = cm.open_campaign(campaign_id)
        db.set_db_path(path)
        db.init_db()
        self.query_one("#campaign-status", Static).update(f"[green]Opened: {campaign['name']}[/green]")
        self.dismiss()

    def _rename_selected(self):
        campaign_id = self._selected_campaign_id()
        if campaign_id is None:
            self.query_one("#campaign-status", Static).update("[yellow]Select a campaign first[/yellow]")
            return
        new_name = self.query_one("#input-campaign-name", Input).value.strip()
        if not new_name:
            self.query_one("#campaign-status", Static).update("[yellow]Enter the new name in the field below first[/yellow]")
            return
        cm.rename_campaign(campaign_id, new_name)
        self.query_one("#input-campaign-name", Input).value = ""
        self._refresh_table()
        self.query_one("#campaign-status", Static).update(f"[green]Renamed to '{new_name}'[/green]")

    def _delete_selected(self):
        campaign_id = self._selected_campaign_id()
        if campaign_id is None:
            self.query_one("#campaign-status", Static).update("[yellow]Select a campaign first[/yellow]")
            return
        campaign = cm.get_campaign(campaign_id)
        if not campaign:
            return
        current_path = str(db.db_path().resolve())
        if str(campaign["path"]) == current_path:
            self.query_one("#campaign-status", Static).update("[red]Cannot delete the currently open campaign[/red]")
            return
        self.app.push_screen(
            ConfirmScreen(f"Remove '{campaign['name']}' from the list? (File is NOT deleted.)"),
            callback=lambda confirmed: self._on_delete_confirmed(confirmed, campaign_id),
        )

    def _on_delete_confirmed(self, confirmed: bool, campaign_id: int):
        if confirmed:
            cm.delete_campaign(campaign_id, delete_file=False)
            self._refresh_table()
            self.query_one("#campaign-status", Static).update("[green]Campaign removed from list[/green]")

    def _create_campaign(self):
        name = self.query_one("#input-campaign-name", Input).value.strip()
        if not name:
            self.query_one("#campaign-status", Static).update("[yellow]Enter a campaign name[/yellow]")
            return
        campaign = cm.create_campaign(name)
        path = cm.open_campaign(campaign["id"])
        db.set_db_path(path)
        db.init_db()
        self.query_one("#input-campaign-name", Input).value = ""
        self.query_one("#campaign-status", Static).update(f"[green]Created and opened: {name}[/green]")
        self.dismiss()

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id
        if bid == "btn-campaign-open":
            self._open_selected()
        elif bid == "btn-campaign-rename":
            self._rename_selected()
        elif bid == "btn-campaign-delete":
            self._delete_selected()
        elif bid == "btn-campaign-create":
            self._create_campaign()
