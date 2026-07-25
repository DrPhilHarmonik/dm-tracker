from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Button, DataTable, Static
from textual.containers import Container, Horizontal
from rich.text import Text

import db
import cal
from screens.common import DismissableScreen, PALETTE, tint_border


class TimelineScreen(DismissableScreen):
    BINDINGS = [
        Binding("escape", "dismiss_screen", "Back"),
        Binding("enter", "open_selected", "Open"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("Session Timeline", id="timeline-heading"),
            Horizontal(
                Button("Open Session", id="btn-open-session", variant="primary"),
                Button("Back", id="btn-back", variant="default"),
                id="timeline-toolbar",
            ),
            DataTable(id="timeline-table", cursor_type="row"),
            id="timeline-container",
        )
        yield Footer()

    def on_mount(self):
        self.title = "Session Timeline"
        tint_border(self.query_one("#timeline-container"), "session")
        table = self.query_one("#timeline-table", DataTable)
        table.add_columns("#", "In-Game Date", "Real Date", "Name", "Notes")
        self._load()

    def _load(self):
        table = self.query_one("#timeline-table", DataTable)
        table.clear()
        sessions = cal.sort_sessions(db.list_entities("session"))
        for s in sessions:
            f = s["fields"]
            num = str(f.get("session_number", "")) or "--"
            in_game = f.get("in_game_date", "") or "--"
            real_date = f.get("session_date", "") or "--"
            notes = s.get("notes", "")
            preview = notes[:60].replace("\n", " ") + ("..." if len(notes) > 60 else "")
            table.add_row(
                Text(num, style="dim"),
                Text(in_game, style=f"bold {PALETTE.get('session', '')}"),
                Text(real_date, style="dim"),
                Text(s["name"]),
                Text(preview, style="dim"),
                key=str(s["id"]),
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        self._open_row(str(event.row_key.value))

    def action_open_selected(self):
        table = self.query_one("#timeline-table", DataTable)
        if table.row_count == 0 or table.cursor_row is None:
            return
        cell_key = table.coordinate_to_cell_key(table.cursor_coordinate)
        self._open_row(str(cell_key.row_key.value))

    def _open_row(self, session_id_str: str):
        from screens.entities import EntityDetailScreen
        self.app.push_screen(
            EntityDetailScreen(int(session_id_str)),
            callback=lambda _: self._load(),
        )

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-open-session":
            self.action_open_selected()
        elif event.button.id == "btn-back":
            self.dismiss()
