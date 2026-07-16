from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Static, Button, DataTable
from textual.containers import Horizontal, ScrollableContainer
from rich.text import Text

import db
import session_workflow as wf
from models import ENTITY_LABELS

from screens.common import DismissableScreen, PALETTE, tint_border


class SessionWorkflowScreen(DismissableScreen):
    BINDINGS = [
        Binding("escape", "dismiss_screen", "Back"),
    ]

    def __init__(self, session_id: int):
        super().__init__()
        self.session_id = session_id

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(
            Static("Player Characters", classes="workflow-heading"),
            DataTable(id="wf-pcs", cursor_type="row"),
            Horizontal(
                Button("Character Sheet", id="btn-wf-pc-sheet", variant="warning"),
                Button("Roll Dice", id="btn-wf-pc-roll", variant="success"),
                id="wf-pc-actions",
            ),
            Static("Active Quests", classes="workflow-heading"),
            DataTable(id="wf-quests", cursor_type="row"),
            Static("Active Encounters", classes="workflow-heading"),
            DataTable(id="wf-encounters", cursor_type="row"),
            Static("Notable NPCs", classes="workflow-heading"),
            DataTable(id="wf-npcs", cursor_type="row"),
            Static("Recent Notes", classes="workflow-heading"),
            DataTable(id="wf-notes", cursor_type="row"),
            id="session-workflow-scroll",
        )
        yield Footer()

    def on_mount(self):
        session = db.get_entity(self.session_id)
        self.title = f"Session Workflow — {session['name']}" if session else "Session Workflow"
        tint_border(self.query_one("#session-workflow-scroll"), "session")
        for table_id, columns in (
            ("wf-pcs", ("Name", "Class", "Level")),
            ("wf-quests", ("Name", "Difficulty", "Objectives")),
            ("wf-encounters", ("Name", "Status", "Location")),
            ("wf-npcs", ("Name", "Race", "Role")),
            ("wf-notes", ("Name", "Type", "Updated")),
        ):
            self.query_one(f"#{table_id}", DataTable).add_columns(*columns)
        self._load()

    def _load(self):
        self._fill("wf-pcs", wf.player_characters(),
                    lambda e: (e["fields"].get("class_name", ""), str(e["fields"].get("level", ""))))
        self._fill("wf-quests", wf.active_quests(),
                    lambda e: (e["fields"].get("difficulty", ""), self._objective_progress_text(e)))
        self._fill("wf-encounters", wf.active_encounters(),
                    lambda e: (e["fields"].get("status", ""), e["fields"].get("location", "")))
        self._fill("wf-npcs", wf.notable_npcs(),
                    lambda e: (e["fields"].get("race", ""), e["fields"].get("role", "")))
        self._fill("wf-notes", wf.recent_notes(),
                    lambda e: (ENTITY_LABELS[e["type"]], e["updated_at"]))

    def _fill(self, table_id, entities, extra_cols):
        table = self.query_one(f"#{table_id}", DataTable)
        table.clear()
        for e in entities:
            cols = (Text(e["name"], style=f"bold {PALETTE.get(e['type'], '')}"),) + tuple(extra_cols(e))
            table.add_row(*cols, key=str(e["id"]))

    def _objective_progress_text(self, quest: dict) -> str:
        done, total = db.objective_progress(quest["fields"])
        if total == 0:
            return "No objectives"
        return f"{done} / {total} complete"

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        from screens.entities import EntityDetailScreen
        from screens.sheet import CharacterSheetScreen
        from screens.combat import CombatTrackerScreen

        entity_id = int(event.row_key.value)
        table_id = event.data_table.id
        if table_id == "wf-pcs":
            self.app.push_screen(CharacterSheetScreen(entity_id), callback=lambda _: self._load())
        elif table_id == "wf-encounters":
            self.app.push_screen(CombatTrackerScreen(entity_id), callback=lambda _: self._load())
        else:
            self.app.push_screen(EntityDetailScreen(entity_id), callback=lambda _: self._load())

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-wf-pc-sheet":
            self._open_selected_pc("sheet")
        elif event.button.id == "btn-wf-pc-roll":
            self._open_selected_pc("roll")

    def _open_selected_pc(self, mode: str):
        from screens.sheet import CharacterSheetScreen
        from screens.roll import RollPickerScreen

        table = self.query_one("#wf-pcs", DataTable)
        if table.row_count == 0 or table.cursor_row is None:
            return
        cell_key = table.coordinate_to_cell_key(table.cursor_coordinate)
        entity_id = int(cell_key.row_key.value)
        if mode == "sheet":
            self.app.push_screen(CharacterSheetScreen(entity_id), callback=lambda _: self._load())
        else:
            self.app.push_screen(RollPickerScreen(entity_id))
