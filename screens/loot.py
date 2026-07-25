from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Button, DataTable, Input, Label, Select, Static
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from rich.text import Text

import db
from screens.common import DismissableScreen, PALETTE, tint_border


class AddLootModal(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "save", "Add"),
    ]

    def compose(self) -> ComposeResult:
        yield Container(
            Label("Item Name"),
            Input(placeholder="Longsword +1", id="loot-name"),
            Label("Quantity"),
            Input(value="1", placeholder="1", id="loot-qty"),
            Label("Value (optional)"),
            Input(placeholder="150 gp", id="loot-value"),
            Horizontal(
                Button("Add (Ctrl+S)", id="btn-add-loot", variant="success"),
                Button("Cancel", id="btn-cancel-loot"),
                id="add-loot-actions",
            ),
            id="add-loot-modal",
        )

    def on_mount(self):
        self.query_one("#loot-name", Input).focus()

    def action_save(self):
        name = self.query_one("#loot-name", Input).value.strip()
        if not name:
            return
        qty = self.query_one("#loot-qty", Input).value.strip() or "1"
        value = self.query_one("#loot-value", Input).value.strip()
        self.dismiss((name, qty, value))

    def action_cancel(self):
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-add-loot":
            self.action_save()
        elif event.button.id == "btn-cancel-loot":
            self.action_cancel()


class AssignLootModal(ModalScreen):
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, options: list[tuple[str, str]]):
        super().__init__()
        self._options = options

    def compose(self) -> ComposeResult:
        yield Container(
            Label("Assign to adventurer:"),
            Select(self._options, id="assign-select", prompt="Select adventurer..."),
            Horizontal(
                Button("Assign", id="btn-confirm-assign", variant="primary"),
                Button("Cancel", id="btn-cancel-assign"),
                id="assign-loot-actions",
            ),
            id="assign-loot-modal",
        )

    def action_cancel(self):
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-confirm-assign":
            sel = self.query_one("#assign-select", Select)
            if sel.value is not Select.NULL:
                self.dismiss(str(sel.value))
        elif event.button.id == "btn-cancel-assign":
            self.dismiss(None)


class LootScreen(DismissableScreen):
    BINDINGS = [
        Binding("escape", "dismiss_screen", "Back"),
        Binding("a", "add_item", "Add Item"),
        Binding("delete", "remove_item", "Remove"),
    ]

    def __init__(self, session_id: int):
        super().__init__()
        self.session_id = session_id

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("", id="loot-session-label"),
            DataTable(id="loot-table", cursor_type="row"),
            Horizontal(
                Button("Add Item", id="btn-add-loot", variant="success"),
                Button("Assign", id="btn-assign-loot", variant="primary"),
                Button("Unassign", id="btn-unassign-loot", variant="warning"),
                Button("Remove", id="btn-remove-loot", variant="error"),
                Button("Back", id="btn-back", variant="default"),
                id="loot-actions",
            ),
            id="loot-container",
        )
        yield Footer()

    def on_mount(self):
        session = db.get_entity(self.session_id)
        self.title = f"Loot -- {session['name']}" if session else "Loot"
        tint_border(self.query_one("#loot-container"), "item")
        table = self.query_one("#loot-table", DataTable)
        table.add_columns("Item", "Qty", "Value", "Owner")
        self._load()

    def _load(self):
        table = self.query_one("#loot-table", DataTable)
        table.clear()
        session = db.get_entity(self.session_id)
        if not session:
            return
        loot = session["fields"].get("loot", [])
        label = self.query_one("#loot-session-label", Static)
        label.update(f"[dim]{len(loot)} item(s)[/dim]" if loot else "[dim]No loot recorded.[/dim]")
        for i, entry in enumerate(loot):
            owner = entry.get("owner", "")
            owner_cell = Text(owner) if owner else Text("Unassigned", style="dim")
            table.add_row(
                Text(entry["name"], style=f"bold {PALETTE.get('item', '')}"),
                entry.get("qty", "1"),
                entry.get("value", "") or "--",
                owner_cell,
                key=str(i),
            )

    def _current_index(self) -> int | None:
        table = self.query_one("#loot-table", DataTable)
        if table.row_count == 0 or table.cursor_row is None:
            return None
        cell_key = table.coordinate_to_cell_key(table.cursor_coordinate)
        return int(cell_key.row_key.value)

    def action_add_item(self):
        self.app.push_screen(AddLootModal(), callback=self._on_add_loot)

    def _on_add_loot(self, result: tuple | None):
        if result:
            name, qty, value = result
            db.add_loot_entry(self.session_id, name, qty, value)
            self._load()

    def action_remove_item(self):
        index = self._current_index()
        if index is None:
            return
        db.remove_loot_entry(self.session_id, index)
        self._load()

    def _assign_selected(self):
        index = self._current_index()
        if index is None:
            return
        adventurers = db.list_entities("adventurer")
        if not adventurers:
            self.app.notify("No adventurers in this campaign", severity="warning")
            return
        options = [(a["name"], a["name"]) for a in adventurers]
        self.app.push_screen(
            AssignLootModal(options),
            callback=lambda owner: self._on_assign(index, owner),
        )

    def _on_assign(self, index: int, owner: str | None):
        if owner is not None:
            db.assign_loot(self.session_id, index, owner)
            self._load()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-add-loot":
            self.action_add_item()
        elif event.button.id == "btn-assign-loot":
            self._assign_selected()
        elif event.button.id == "btn-unassign-loot":
            index = self._current_index()
            if index is not None:
                db.assign_loot(self.session_id, index, "")
                self._load()
        elif event.button.id == "btn-remove-loot":
            self.action_remove_item()
        elif event.button.id == "btn-back":
            self.dismiss()
