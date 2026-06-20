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

from screens.common import DismissableScreen, PALETTE
from screens.modals import ConfirmScreen
from screens.sheet import CharacterSheetScreen
from screens.roll import RollPickerScreen
from screens.combat import CombatTrackerScreen
from screens.effects import EffectsScreen
from screens.wizard import WizardScreen

class EntityListScreen(DismissableScreen):
    BINDINGS = [
        Binding("escape", "dismiss_screen", "Back"),
        Binding("a", "add", "Add"),
        Binding("d", "delete", "Delete"),
        Binding("enter", "open_selected", "Open"),
        Binding("/", "focus_search", "Search"),
    ]

    def __init__(self, type_: str):
        super().__init__()
        self.type_ = type_
        self.label = ENTITY_LABELS[type_]
        self.label_plural = ENTITY_LABELS_PLURAL[type_]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Horizontal(
                Input(placeholder=f"Search {self.label_plural}...", id="search"),
                Button("+ Add", id="btn-add", variant="primary"),
                Button("Quick Wizard", id="btn-wizard-quick", variant="success"),
                Button("Advanced Wizard", id="btn-wizard-advanced", variant="warning"),
                id="list-toolbar",
            ),
            DataTable(id="entity-table", cursor_type="row"),
            id="list-container",
        )
        yield Footer()

    def on_mount(self):
        self.title = self.label_plural
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
        elif event.button.id == "btn-wizard-quick":
            self.action_wizard("quick")
        elif event.button.id == "btn-wizard-advanced":
            self.action_wizard("advanced")

    def action_add(self):
        self.app.push_screen(EntityFormScreen(self.type_), callback=self._on_form_done)

    def action_wizard(self, mode: str):
        self.app.push_screen(WizardScreen(self.type_, mode), callback=lambda _: self._load())

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

class GlobalSearchScreen(DismissableScreen):
    BINDINGS = [
        Binding("escape", "dismiss_screen", "Back"),
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


def _schema_choices(entity_type: str, key: str) -> list[str]:
    for field_key, _, _, choices in ENTITY_SCHEMAS.get(entity_type, []):
        if field_key == key and choices:
            return choices
    return []


# ---------------------------------------------------------------------------
# Entity Detail
# ---------------------------------------------------------------------------

def _format_sheet_lines(entity_type: str, raw_sheet: dict, raw_effects: list | None = None) -> list[str]:
    base_sheet = shm.normalize_sheet(raw_sheet)
    active_effects = fx.normalize_effects(raw_effects)
    sheet = fx.apply_to_sheet(base_sheet, active_effects)
    pb = shm.proficiency_bonus(entity_type, sheet)

    lines = ["", "[bold]Character Sheet:[/]"]
    ability_parts = [
        f"{a.upper()} {sheet['abilities'][a]} ({shm.format_modifier(shm.ability_modifier(sheet['abilities'][a]))})"
        for a in shm.ABILITIES
    ]
    lines.append("  " + "  ".join(ability_parts))

    hp_line = f"  AC {sheet['ac']}   HP {sheet['hp_current']}/{sheet['hp_max']}"
    if sheet["hp_temp"]:
        hp_line += f" (+{sheet['hp_temp']} temp)"
    hp_line += f"   Speed {sheet['speed']} ft.   Prof. Bonus {shm.format_modifier(pb)}"
    lines.append(hp_line)

    if entity_type == "enemy":
        lines.append(f"  CR {sheet['cr']}   {sheet['creature_type']}".rstrip())
    else:
        lines.append(f"  Level {sheet['level']}")

    if sheet["saving_throw_proficiencies"]:
        saves = ", ".join(
            f"{a.upper()} {shm.format_modifier(shm.saving_throw_bonus(sheet, a, pb))}"
            for a in shm.ABILITIES if a in sheet["saving_throw_proficiencies"]
        )
        lines.append(f"  Saves: {saves}")

    proficient_skills = [s for s in shm.SKILLS if sheet["skill_proficiencies"].get(s, "none") != "none"]
    if proficient_skills:
        skills_str = ", ".join(
            f"{shm.SKILL_LABELS[s]} {shm.format_modifier(shm.skill_bonus(sheet, s, pb))}"
            for s in proficient_skills
        )
        lines.append(f"  Skills: {skills_str}")

    if sheet["attacks"]:
        lines.append("  Attacks:")
        for atk in sheet["attacks"]:
            bonus = shm.format_modifier(int(atk.get("bonus", 0) or 0))
            lines.append(f"    {atk.get('name', '?')} {bonus} to hit, {atk.get('damage', '')} {atk.get('damage_type', '')}".rstrip())

    for label, key in (("Resistances", "resistances"), ("Immunities", "immunities"), ("Vulnerabilities", "vulnerabilities")):
        if sheet[key]:
            lines.append(f"  {label}: {sheet[key]}")

    if sheet["special_abilities"]:
        lines.append("  Special Abilities:")
        for sa in sheet["special_abilities"]:
            lines.append(f"    {sa.get('name', '?')}: {sa.get('description', '')}")

    for label, key in (("Senses", "senses"), ("Languages", "languages")):
        if sheet[key]:
            lines.append(f"  {label}: {sheet[key]}")

    if active_effects:
        lines.append("  Active Effects:")
        for effect in active_effects:
            duration = f"{effect['rounds_remaining']} rounds left" if effect["rounds_remaining"] is not None else "indefinite"
            modifier = shm.format_modifier(effect["modifier"])
            lines.append(f"    {effect['source']}: {modifier} {fx.STAT_LABELS[effect['stat']]} ({duration})")

    return lines


class EntityDetailScreen(DismissableScreen):
    BINDINGS = [
        Binding("escape", "dismiss_screen", "Back"),
        Binding("e", "edit", "Edit"),
        Binding("r", "add_rel", "Add Relation"),
        Binding("d", "del_rel", "Delete Relation"),
        Binding("c", "open_sheet", "Character Sheet"),
        Binding("k", "open_roll", "Roll Dice"),
        Binding("h", "make_hostile", "Make Hostile"),
        Binding("o", "open_combat", "Combat Tracker"),
        Binding("f", "open_effects", "Effects"),
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

    async def on_mount(self):
        self._render_detail()
        entity = db.get_entity(self.entity_id)
        if not entity:
            return
        actions = self.query_one("#detail-actions")
        if entity["type"] in shm.SHEET_ENTITY_TYPES:
            await actions.mount(
                Button("Character Sheet", id="btn-sheet", variant="warning"),
                Button("Roll Dice", id="btn-roll", variant="success"),
                Button("Effects", id="btn-effects", variant="default"),
            )
        if entity["type"] == "npc":
            await actions.mount(Button("Make Hostile", id="btn-hostile", variant="error"))
        if entity["type"] == "encounter":
            await actions.mount(Button("Combat Tracker", id="btn-combat", variant="warning"))

    def _render_detail(self):
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

        if entity["type"] in shm.SHEET_ENTITY_TYPES:
            lines.extend(_format_sheet_lines(entity["type"], entity["fields"].get("sheet", {}), entity["fields"].get("active_effects", [])))

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
            self.dismiss()
        elif event.button.id == "btn-sheet":
            self.action_open_sheet()
        elif event.button.id == "btn-roll":
            self.action_open_roll()
        elif event.button.id == "btn-hostile":
            self.action_make_hostile()
        elif event.button.id == "btn-combat":
            self.action_open_combat()
        elif event.button.id == "btn-effects":
            self.action_open_effects()

    def action_edit(self):
        entity = db.get_entity(self.entity_id)
        self.app.push_screen(EntityFormScreen(entity["type"], entity), callback=lambda _: self._render_detail())

    def action_add_rel(self):
        self.app.push_screen(RelationshipFormScreen(self.entity_id), callback=lambda _: self._render_detail())

    def action_del_rel(self):
        self.app.push_screen(DeleteRelScreen(self.entity_id), callback=lambda _: self._render_detail())

    def action_open_sheet(self):
        entity = db.get_entity(self.entity_id)
        if entity and entity["type"] in shm.SHEET_ENTITY_TYPES:
            self.app.push_screen(CharacterSheetScreen(self.entity_id), callback=lambda _: self._render_detail())

    def action_open_roll(self):
        entity = db.get_entity(self.entity_id)
        if entity and entity["type"] in shm.SHEET_ENTITY_TYPES:
            self.app.push_screen(RollPickerScreen(self.entity_id))

    def action_make_hostile(self):
        entity = db.get_entity(self.entity_id)
        if entity and entity["type"] == "npc":
            self.app.push_screen(
                ConfirmScreen(f"Create a hostile Enemy version of {entity['name']}?"),
                callback=self._on_make_hostile_confirmed,
            )

    def _on_make_hostile_confirmed(self, confirmed: bool):
        if not confirmed:
            return
        entity = db.get_entity(self.entity_id)
        fields = entity["fields"]
        prefill = {
            "name": f"{entity['name']} (Hostile)",
            "creature_type": fields.get("race", ""),
            "alignment": fields.get("alignment", ""),
        }
        self.app.push_screen(
            WizardScreen("enemy", "quick", prefill=prefill, link_to_npc_id=self.entity_id),
            callback=lambda _: self._render_detail(),
        )

    def action_open_combat(self):
        entity = db.get_entity(self.entity_id)
        if entity and entity["type"] == "encounter":
            self.app.push_screen(CombatTrackerScreen(self.entity_id), callback=lambda _: self._render_detail())

    def action_open_effects(self):
        entity = db.get_entity(self.entity_id)
        if entity and entity["type"] in shm.SHEET_ENTITY_TYPES:
            self.app.push_screen(EffectsScreen(self.entity_id), callback=lambda _: self._render_detail())


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
