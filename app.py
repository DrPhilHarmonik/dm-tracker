from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Label, Button, DataTable, Input, Select, TextArea, Static, ListView, ListItem
from textual.screen import Screen, ModalScreen
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual import on, work
from textual.reactive import reactive
from rich.text import Text
import db
import export as exp
from models import ENTITY_TYPES, ENTITY_LABELS, ENTITY_SCHEMAS, RELATIONSHIP_TYPES
from pathlib import Path


PALETTE = {
    "npc":        "#c792ea",
    "adventurer": "#89ddff",
    "location":   "#c3e88d",
    "quest":      "#ffcb6b",
    "faction":    "#f78c6c",
    "item":       "#82aaff",
    "session":    "#b2ccd6",
}


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class Dashboard(Screen):
    BINDINGS = [
        Binding("n", "goto('npc')", "NPCs"),
        Binding("a", "goto('adventurer')", "Adventurers"),
        Binding("l", "goto('location')", "Locations"),
        Binding("q", "goto('quest')", "Quests"),
        Binding("f", "goto('faction')", "Factions"),
        Binding("i", "goto('item')", "Items"),
        Binding("s", "goto('session')", "Sessions"),
        Binding("e", "export", "Export MD"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("[bold]DM Tracker[/bold] - Campaign Manager", id="title"),
            Container(id="cards"),
            Container(
                Button("Export to Markdown", id="btn-export", variant="success"),
                id="actions",
            ),
            id="dashboard",
        )
        yield Footer()

    def on_mount(self):
        self.refresh_cards()

    def refresh_cards(self):
        counts = db.entity_counts()
        cards = self.query_one("#cards")
        cards.remove_children()
        for type_ in ENTITY_TYPES:
            count = counts.get(type_, 0)
            label = ENTITY_LABELS[type_]
            color = PALETTE[type_]
            card = Button(
                f"[bold]{label}s[/bold]\n{count} entries",
                id=f"card-{type_}",
                classes="card",
            )
            cards.mount(card)

    def on_button_pressed(self, event: Button.Pressed):
        btn_id = event.button.id
        if btn_id and btn_id.startswith("card-"):
            type_ = btn_id[5:]
            self.app.push_screen(EntityListScreen(type_))
        elif btn_id == "btn-export":
            self.action_export()

    def action_goto(self, type_: str):
        self.app.push_screen(EntityListScreen(type_))

    def action_export(self):
        self.app.push_screen(ExportScreen())


# ---------------------------------------------------------------------------
# Entity List
# ---------------------------------------------------------------------------

class EntityListScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("a", "add", "Add"),
        Binding("d", "delete", "Delete"),
        Binding("enter", "open_selected", "Open"),
        Binding("/", "focus_search", "Search"),
    ]

    def __init__(self, type_: str):
        super().__init__()
        self.type_ = type_
        self.label = ENTITY_LABELS[type_]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Horizontal(
                Input(placeholder=f"Search {self.label}s...", id="search"),
                Button("+ Add", id="btn-add", variant="primary"),
                id="list-toolbar",
            ),
            DataTable(id="entity-table", cursor_type="row"),
            id="list-container",
        )
        yield Footer()

    def on_mount(self):
        self.title = f"{self.label}s"
        table = self.query_one(DataTable)
        table.add_columns("Name", *[label for _, label, _, _ in ENTITY_SCHEMAS.get(self.type_, [])][:3])
        self._load()

    def _load(self, search: str = None):
        table = self.query_one(DataTable)
        table.clear()
        entities = db.list_entities(self.type_, search)
        schema = ENTITY_SCHEMAS.get(self.type_, [])
        keys = [k for k, *_ in schema][:3]
        for e in entities:
            cols = [Text(e["name"], style=f"bold {PALETTE[self.type_]}")] + [
                str(e["fields"].get(k, "")) for k in keys
            ]
            table.add_row(*cols, key=str(e["id"]))

    @on(Input.Changed, "#search")
    def on_search(self, event: Input.Changed):
        self._load(event.value or None)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-add":
            self.action_add()

    def action_add(self):
        self.app.push_screen(EntityFormScreen(self.type_), callback=self._on_form_done)

    def action_delete(self):
        table = self.query_one(DataTable)
        if table.cursor_row is None:
            return
        row_key = table.get_row_at(table.cursor_row)
        cell_key = table.coordinate_to_cell_key(table.cursor_coordinate)
        entity_id = int(cell_key.row_key.value)
        self.app.push_screen(ConfirmScreen(f"Delete this {self.label}?"), callback=lambda ok: self._do_delete(ok, entity_id))

    def _do_delete(self, confirmed: bool, entity_id: int):
        if confirmed:
            db.delete_entity(entity_id)
            self._load()

    def action_open_selected(self):
        table = self.query_one(DataTable)
        if table.row_count == 0:
            return
        cell_key = table.coordinate_to_cell_key(table.cursor_coordinate)
        entity_id = int(cell_key.row_key.value)
        self.app.push_screen(EntityDetailScreen(entity_id), callback=lambda _: self._load())

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        entity_id = int(event.row_key.value)
        self.app.push_screen(EntityDetailScreen(entity_id), callback=lambda _: self._load())

    def _on_form_done(self, _):
        self._load()

    def action_focus_search(self):
        self.query_one("#search").focus()


# ---------------------------------------------------------------------------
# Entity Detail
# ---------------------------------------------------------------------------

class EntityDetailScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("e", "edit", "Edit"),
        Binding("r", "add_rel", "Add Relation"),
        Binding("d", "del_rel", "Delete Relation"),
    ]

    def __init__(self, entity_id: int):
        super().__init__()
        self.entity_id = entity_id

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(
            Static(id="detail-body"),
            id="detail-scroll",
        )
        yield Container(
            Button("Edit", id="btn-edit", variant="primary"),
            Button("Add Relationship", id="btn-rel", variant="default"),
            Button("Back", id="btn-back", variant="default"),
            id="detail-actions",
        )
        yield Footer()

    def on_mount(self):
        self._render()

    def _render(self):
        entity = db.get_entity(self.entity_id)
        if not entity:
            self.dismiss()
            return
        self.title = entity["name"]
        schema = ENTITY_SCHEMAS.get(entity["type"], [])
        rels = db.get_relationships(self.entity_id)

        lines = [f"[bold {PALETTE[entity['type']]}]{entity['name']}[/]",
                 f"[dim]{ENTITY_LABELS[entity['type']]}[/]", ""]

        for key, label, *_ in schema:
            val = entity["fields"].get(key, "")
            if val:
                lines.append(f"[bold]{label}:[/] {val}")

        if rels:
            lines.append("")
            lines.append("[bold]Relationships:[/]")
            for r in rels:
                if r["from_id"] == self.entity_id:
                    other = r["to_name"]
                    direction = r["rel_type"]
                else:
                    other = r["from_name"]
                    direction = f"(reverse) {r['rel_type']}"
                note = f"  [dim]{r['notes']}[/dim]" if r.get("notes") else ""
                lines.append(f"  [cyan]{direction}[/] -> [yellow]{other}[/]{note}  [dim](id:{r['id']})[/dim]")

        notes = entity.get("notes", "").strip()
        if notes:
            lines.append("")
            lines.append("[bold]Notes:[/]")
            lines.append(notes)

        self.query_one("#detail-body", Static).update("\n".join(lines))

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-edit":
            self.action_edit()
        elif event.button.id == "btn-rel":
            self.action_add_rel()
        elif event.button.id == "btn-back":
            self.app.pop_screen()

    def action_edit(self):
        entity = db.get_entity(self.entity_id)
        self.app.push_screen(EntityFormScreen(entity["type"], entity), callback=lambda _: self._render())

    def action_add_rel(self):
        self.app.push_screen(RelationshipFormScreen(self.entity_id), callback=lambda _: self._render())

    def action_del_rel(self):
        self.app.push_screen(DeleteRelScreen(self.entity_id), callback=lambda _: self._render())


# ---------------------------------------------------------------------------
# Entity Form (Add / Edit)
# ---------------------------------------------------------------------------

class EntityFormScreen(Screen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "save", "Save"),
    ]

    def __init__(self, type_: str, entity: dict = None):
        super().__init__()
        self.type_ = type_
        self.entity = entity  # None = create mode
        self.schema = ENTITY_SCHEMAS.get(type_, [])

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(
            Container(id="form-fields"),
            id="form-scroll",
        )
        yield Container(
            Button("Save (Ctrl+S)", id="btn-save", variant="success"),
            Button("Cancel", id="btn-cancel", variant="default"),
            id="form-actions",
        )
        yield Footer()

    def on_mount(self):
        label = ENTITY_LABELS[self.type_]
        self.title = f"{'Edit' if self.entity else 'New'} {label}"
        container = self.query_one("#form-fields")
        existing = self.entity["fields"] if self.entity else {}
        existing_name = self.entity["name"] if self.entity else ""

        container.mount(Label("Name"))
        container.mount(Input(value=existing_name, placeholder="Name", id="field-name"))

        for key, field_label, ftype, choices in self.schema:
            container.mount(Label(field_label))
            val = existing.get(key, "")
            if ftype == "select" and choices:
                options = [(c, c) for c in choices]
                sel = Select(options, value=val or Select.BLANK, id=f"field-{key}")
                container.mount(sel)
            else:
                container.mount(Input(value=str(val) if val else "", placeholder=field_label, id=f"field-{key}"))

        container.mount(Label("Notes"))
        notes_val = self.entity.get("notes", "") if self.entity else ""
        container.mount(TextArea(notes_val, id="field-notes", language=None))

    def _collect(self) -> tuple[str, dict, str] | None:
        name = self.query_one("#field-name", Input).value.strip()
        if not name:
            return None
        fields = {}
        for key, _, ftype, choices in self.schema:
            widget_id = f"field-{key}"
            if ftype == "select" and choices:
                sel = self.query_one(f"#{widget_id}", Select)
                fields[key] = "" if sel.value is Select.BLANK else str(sel.value)
            else:
                fields[key] = self.query_one(f"#{widget_id}", Input).value.strip()
        notes = self.query_one("#field-notes", TextArea).text
        return name, fields, notes

    def action_save(self):
        result = self._collect()
        if not result:
            return
        name, fields, notes = result
        if self.entity:
            db.update_entity(self.entity["id"], name, fields, notes)
        else:
            db.create_entity(self.type_, name, fields, notes)
        self.dismiss(True)

    def action_cancel(self):
        self.dismiss(False)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-save":
            self.action_save()
        elif event.button.id == "btn-cancel":
            self.action_cancel()


# ---------------------------------------------------------------------------
# Relationship Form
# ---------------------------------------------------------------------------

class RelationshipFormScreen(Screen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "save", "Save"),
    ]

    def __init__(self, from_id: int):
        super().__init__()
        self.from_id = from_id

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(
            Container(id="rel-form"),
            id="rel-scroll",
        )
        yield Container(
            Button("Save (Ctrl+S)", id="btn-save", variant="success"),
            Button("Cancel", id="btn-cancel", variant="default"),
            id="rel-actions",
        )
        yield Footer()

    def on_mount(self):
        self.title = "Add Relationship"
        container = self.query_one("#rel-form")
        all_entities = db.list_entities()
        entity_options = [(f"{e['name']} ({ENTITY_LABELS[e['type']]})", str(e["id"])) for e in all_entities if e["id"] != self.from_id]
        rel_options = [(r, r) for r in RELATIONSHIP_TYPES]

        container.mount(Label("Target Entity"))
        container.mount(Select(entity_options, id="sel-target", prompt="Select entity..."))
        container.mount(Label("Relationship Type"))
        container.mount(Select(rel_options, id="sel-reltype", prompt="Select type..."))
        container.mount(Label("Notes (optional)"))
        container.mount(Input(placeholder="e.g. 'sworn enemies since the siege'", id="rel-notes"))

    def action_save(self):
        target_sel = self.query_one("#sel-target", Select)
        reltype_sel = self.query_one("#sel-reltype", Select)
        if target_sel.value is Select.BLANK or reltype_sel.value is Select.BLANK:
            return
        to_id = int(str(target_sel.value))
        rel_type = str(reltype_sel.value)
        notes = self.query_one("#rel-notes", Input).value.strip()
        db.create_relationship(self.from_id, to_id, rel_type, notes)
        self.dismiss(True)

    def action_cancel(self):
        self.dismiss(False)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-save":
            self.action_save()
        elif event.button.id == "btn-cancel":
            self.action_cancel()


# ---------------------------------------------------------------------------
# Delete Relationship
# ---------------------------------------------------------------------------

class DeleteRelScreen(Screen):
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, entity_id: int):
        super().__init__()
        self.entity_id = entity_id

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("Select a relationship to delete:"),
            ListView(id="rel-list"),
            Button("Delete Selected", id="btn-del", variant="error"),
            Button("Cancel", id="btn-cancel"),
            id="delrel-container",
        )
        yield Footer()

    def on_mount(self):
        self.title = "Delete Relationship"
        self.rels = db.get_relationships(self.entity_id)
        lv = self.query_one(ListView)
        for r in self.rels:
            if r["from_id"] == self.entity_id:
                label = f"{r['rel_type']} -> {r['to_name']} ({r['to_type']})"
            else:
                label = f"[reverse] {r['rel_type']} <- {r['from_name']} ({r['from_type']})"
            lv.append(ListItem(Label(label)))

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-del":
            lv = self.query_one(ListView)
            if lv.index is not None and lv.index < len(self.rels):
                rel_id = self.rels[lv.index]["id"]
                db.delete_relationship(rel_id)
                self.dismiss(True)
        elif event.button.id == "btn-cancel":
            self.dismiss(False)

    def action_cancel(self):
        self.dismiss(False)


# ---------------------------------------------------------------------------
# Confirm Modal
# ---------------------------------------------------------------------------

class ConfirmScreen(ModalScreen):
    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        yield Container(
            Static(self.message),
            Horizontal(
                Button("Yes", id="btn-yes", variant="error"),
                Button("No", id="btn-no", variant="default"),
            ),
            id="confirm-box",
        )

    def on_button_pressed(self, event: Button.Pressed):
        self.dismiss(event.button.id == "btn-yes")


# ---------------------------------------------------------------------------
# Export Screen
# ---------------------------------------------------------------------------

class ExportScreen(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("Export Campaign to Obsidian Vault", id="export-title"),
            Label("Output directory:"),
            Input(value=str(Path.home() / "campaign_vault"), id="export-path"),
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
            try:
                count = exp.export_vault(out_path)
                self.query_one("#export-status", Static).update(
                    f"[green]Exported {count} entities to {out_path}[/green]"
                )
            except Exception as ex:
                self.query_one("#export-status", Static).update(f"[red]Error: {ex}[/red]")
        elif event.button.id == "btn-cancel":
            self.app.pop_screen()


# ---------------------------------------------------------------------------
# App Root
# ---------------------------------------------------------------------------

class DMApp(App):
    CSS_PATH = "dm.tcss"
    TITLE = "DM Tracker"
    SCREENS = {"dashboard": Dashboard}
    BINDINGS = [Binding("ctrl+q", "quit", "Quit")]

    def on_mount(self):
        db.init_db()
        self.push_screen("dashboard")


def main():
    app = DMApp()
    app.run()


if __name__ == "__main__":
    main()
