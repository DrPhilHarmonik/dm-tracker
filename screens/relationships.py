from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Button, DataTable, Select
from textual.containers import Container, Horizontal
from rich.text import Text

import db
from models import ENTITY_TYPES, ENTITY_LABELS
from screens.common import DismissableScreen, PALETTE, tint_border


class RelationshipBrowserScreen(DismissableScreen):
    BINDINGS = [
        Binding("escape", "dismiss_screen", "Back"),
        Binding("enter", "open_selected", "Open"),
    ]

    def __init__(self, focus_entity_id: int | None = None):
        super().__init__()
        self.focus_entity_id = focus_entity_id
        self._row_targets: dict[str, int] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Horizontal(
                Select(
                    [("All Types", "all")] + [(ENTITY_LABELS[t], t) for t in ENTITY_TYPES],
                    value="all",
                    id="relationship-type-filter",
                    allow_blank=False,
                ),
                Button("Open", id="btn-open-relationship", variant="primary"),
                Button("Back", id="btn-back", variant="default"),
                id="relationship-toolbar",
            ),
            DataTable(id="relationship-table", cursor_type="row"),
            id="relationship-browser",
        )
        yield Footer()

    def on_mount(self):
        self.title = "Relationship Browser"
        tint_border(self.query_one("#relationship-browser"), "faction")
        table = self.query_one("#relationship-table", DataTable)
        table.add_columns("Entity", "Type", "Direction", "Relationship", "Related Entity")
        self._load()

    def _selected_type(self) -> str | None:
        value = self.query_one("#relationship-type-filter", Select).value
        if value is Select.NULL or value == "all":
            return None
        return str(value)

    def _load(self):
        table = self.query_one("#relationship-table", DataTable)
        table.clear()
        self._row_targets.clear()
        row_index = 0
        selected_type = self._selected_type()
        entity_groups = [selected_type] if selected_type else ENTITY_TYPES
        for entity_type in entity_groups:
            for entity in db.list_entities(entity_type):
                row_index = self._add_entity_rows(table, entity, row_index)
        self._focus_initial_row()

    def _add_entity_rows(self, table: DataTable, entity: dict, row_index: int) -> int:
        rels = db.get_relationships(entity["id"])
        if not rels:
            key = f"entity:{entity['id']}:{row_index}"
            self._row_targets[key] = entity["id"]
            table.add_row(
                Text(entity["name"], style=f"bold {PALETTE.get(entity['type'], '')}"),
                ENTITY_LABELS[entity["type"]],
                "",
                Text("No relationships", style="dim"),
                "",
                key=key,
            )
            return row_index + 1
        for rel in rels:
            if rel["from_id"] == entity["id"]:
                direction = "out"
                related_id = rel["to_id"]
                related_name = rel["to_name"]
                related_type = rel["to_type"]
            else:
                direction = "in"
                related_id = rel["from_id"]
                related_name = rel["from_name"]
                related_type = rel["from_type"]
            key = f"rel:{entity['id']}:{rel['id']}:{related_id}:{row_index}"
            self._row_targets[key] = related_id
            table.add_row(
                Text(entity["name"], style=f"bold {PALETTE.get(entity['type'], '')}"),
                ENTITY_LABELS[entity["type"]],
                direction,
                rel["rel_type"],
                Text(
                    f"{related_name} ({ENTITY_LABELS[related_type]})",
                    style=f"bold {PALETTE.get(related_type, '')}",
                ),
                key=key,
            )
            row_index += 1
        return row_index

    def _focus_initial_row(self):
        if self.focus_entity_id is None:
            return
        table = self.query_one("#relationship-table", DataTable)
        for row_index, row_key in enumerate(table.rows):
            if str(row_key.value).startswith(f"rel:{self.focus_entity_id}:") or str(row_key.value).startswith(f"entity:{self.focus_entity_id}:"):
                table.move_cursor(row=row_index)
                return

    @on(Select.Changed, "#relationship-type-filter")
    def on_filter_changed(self, event: Select.Changed):
        self._load()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-open-relationship":
            self.action_open_selected()
        elif event.button.id == "btn-back":
            self.dismiss()

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        self._open_row(str(event.row_key.value))

    def action_open_selected(self):
        table = self.query_one("#relationship-table", DataTable)
        if table.row_count == 0 or table.cursor_row is None:
            return
        cell_key = table.coordinate_to_cell_key(table.cursor_coordinate)
        self._open_row(str(cell_key.row_key.value))

    def _open_row(self, row_key: str):
        entity_id = self._row_targets.get(row_key)
        if entity_id is None:
            return
        from screens.entities import EntityDetailScreen
        self.app.push_screen(EntityDetailScreen(entity_id), callback=lambda _: self._load())
