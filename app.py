from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Label, Button, DataTable, Input, Select, TextArea, Static, ListView, ListItem
from textual.screen import Screen, ModalScreen
from textual.containers import Container, Horizontal, ScrollableContainer
from textual import on
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
        Binding("/", "search", "Search All"),
        Binding("b", "backup", "Backup/Restore"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("[bold]DM Tracker[/bold] - Campaign Manager", id="title"),
            Container(id="cards"),
            Container(
                Button("Export to Markdown", id="btn-export", variant="success"),
                Button("Search All", id="btn-search", variant="primary"),
                Button("Backup / Restore", id="btn-backup", variant="default"),
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
        elif btn_id == "btn-search":
            self.action_search()
        elif btn_id == "btn-backup":
            self.action_backup()

    def action_goto(self, type_: str):
        self.app.push_screen(EntityListScreen(type_))

    def action_export(self):
        self.app.push_screen(ExportScreen())

    def action_search(self):
        self.app.push_screen(GlobalSearchScreen())

    def action_backup(self):
        self.app.push_screen(BackupScreen())


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
# Global Search
# ---------------------------------------------------------------------------

class GlobalSearchScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("enter", "open_selected", "Open"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Input(placeholder="Search all entities by name or notes...", id="global-search"),
            DataTable(id="global-table", cursor_type="row"),
            id="global-search-container",
        )
        yield Footer()

    def on_mount(self):
        self.title = "Search All"
        table = self.query_one(DataTable)
        table.add_columns("Name", "Type")
        self.query_one("#global-search", Input).focus()

    @on(Input.Changed, "#global-search")
    def on_search(self, event: Input.Changed):
        self._load(event.value)

    def _load(self, query: str):
        table = self.query_one(DataTable)
        table.clear()
        query = (query or "").strip()
        if not query:
            return
        for e in db.search_all(query):
            table.add_row(
                Text(e["name"], style=f"bold {PALETTE[e['type']]}"),
                ENTITY_LABELS[e["type"]],
                key=str(e["id"]),
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        entity_id = int(event.row_key.value)
        self.app.push_screen(EntityDetailScreen(entity_id))

    def action_open_selected(self):
        table = self.query_one(DataTable)
        if table.row_count == 0:
            return
        cell_key = table.coordinate_to_cell_key(table.cursor_coordinate)
        entity_id = int(cell_key.row_key.value)
        self.app.push_screen(EntityDetailScreen(entity_id))


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
        self.pending_rels: list[dict] = []
        self.target_entities: dict[str, str] = {}

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
                sel = Select(options, value=val or Select.NULL, id=f"field-{key}")
                container.mount(sel)
            else:
                container.mount(Input(value=str(val) if val else "", placeholder=field_label, id=f"field-{key}"))

        container.mount(Label("Notes"))
        notes_val = self.entity.get("notes", "") if self.entity else ""
        container.mount(TextArea(notes_val, id="field-notes", language=None))

        container.mount(Label("Add Relationship (optional)"))
        own_id = self.entity["id"] if self.entity else None
        candidates = [e for e in db.list_entities() if e["id"] != own_id]
        self.target_entities = {str(e["id"]): e["name"] for e in candidates}
        entity_options = [(f"{e['name']} ({ENTITY_LABELS[e['type']]})", str(e["id"])) for e in candidates]
        container.mount(Select(entity_options, id="sel-rel-target", prompt="Select entity..."))
        container.mount(Select([(r, r) for r in RELATIONSHIP_TYPES], id="sel-rel-type", prompt="Select type..."))
        container.mount(Input(placeholder="Relationship notes (optional)", id="input-rel-notes"))
        container.mount(Horizontal(
            Button("+ Add Relationship", id="btn-add-pending-rel"),
            Button("Remove Selected", id="btn-remove-pending-rel"),
            id="pending-rel-actions",
        ))
        container.mount(ListView(id="list-pending-rels"))

    def _refresh_pending_list(self):
        lv = self.query_one("#list-pending-rels", ListView)
        lv.clear()
        for rel in self.pending_rels:
            suffix = f" — {rel['notes']}" if rel["notes"] else ""
            lv.append(ListItem(Label(f"{rel['rel_type']} -> {rel['to_name']}{suffix}")))

    def _add_pending_rel(self):
        target_sel = self.query_one("#sel-rel-target", Select)
        type_sel = self.query_one("#sel-rel-type", Select)
        notes_input = self.query_one("#input-rel-notes", Input)
        if target_sel.value is Select.NULL or type_sel.value is Select.NULL:
            return
        to_id = int(str(target_sel.value))
        self.pending_rels.append({
            "to_id": to_id,
            "to_name": self.target_entities.get(str(to_id), "?"),
            "rel_type": str(type_sel.value),
            "notes": notes_input.value.strip(),
        })
        notes_input.value = ""
        self._refresh_pending_list()

    def _remove_pending_rel(self):
        lv = self.query_one("#list-pending-rels", ListView)
        if lv.index is not None and lv.index < len(self.pending_rels):
            del self.pending_rels[lv.index]
            self._refresh_pending_list()

    def _collect(self) -> tuple[str, dict, str] | None:
        name = self.query_one("#field-name", Input).value.strip()
        if not name:
            return None
        fields = {}
        for key, _, ftype, choices in self.schema:
            widget_id = f"field-{key}"
            if ftype == "select" and choices:
                sel = self.query_one(f"#{widget_id}", Select)
                fields[key] = "" if sel.value is Select.NULL else str(sel.value)
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
            entity_id = self.entity["id"]
        else:
            entity_id = db.create_entity(self.type_, name, fields, notes)
        for rel in self.pending_rels:
            db.create_relationship(entity_id, rel["to_id"], rel["rel_type"], rel["notes"])
        self.dismiss(True)

    def action_cancel(self):
        self.dismiss(False)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-save":
            self.action_save()
        elif event.button.id == "btn-cancel":
            self.action_cancel()
        elif event.button.id == "btn-add-pending-rel":
            self._add_pending_rel()
        elif event.button.id == "btn-remove-pending-rel":
            self._remove_pending_rel()


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
        if target_sel.value is Select.NULL or reltype_sel.value is Select.NULL:
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
# Backup / Restore
# ---------------------------------------------------------------------------

class BackupScreen(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
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
            Button("Back", id="btn-back"),
            id="backup-container",
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
        elif event.button.id == "btn-back":
            self.app.pop_screen()

    def _on_replace_confirmed(self, confirmed: bool):
        if confirmed:
            self._do_restore(replace=True)

    def _do_backup(self):
        path = Path(self.query_one("#backup-path", Input).value.strip()).expanduser()
        try:
            count = exp.export_json_backup(path)
            self.query_one("#backup-status", Static).update(f"[green]Backed up {count} entities to {path}[/green]")
        except Exception as ex:
            self.query_one("#backup-status", Static).update(f"[red]Error: {ex}[/red]")

    def _do_restore(self, replace: bool):
        path = Path(self.query_one("#restore-path", Input).value.strip()).expanduser()
        try:
            result = exp.import_json_backup(path, replace=replace)
            self.query_one("#restore-status", Static).update(
                f"[green]Restored {result['entities']} entities and {result['relationships']} relationships[/green]"
            )
        except Exception as ex:
            self.query_one("#restore-status", Static).update(f"[red]Error: {ex}[/red]")


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
