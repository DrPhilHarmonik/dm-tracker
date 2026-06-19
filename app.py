from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Label, Button, DataTable, Input, Select, TextArea, Static, ListView, ListItem, TabbedContent, TabPane, Switch
from textual.screen import Screen, ModalScreen
from textual.containers import Container, Horizontal, ScrollableContainer
from textual import on
from rich.text import Text
import db
import export as exp
import sheet as shm
import dice
import combat as cbt
from models import ENTITY_TYPES, ENTITY_LABELS, ENTITY_LABELS_PLURAL, ENTITY_SCHEMAS, RELATIONSHIP_TYPES
from pathlib import Path


PALETTE = {
    "npc":        "#c792ea",
    "adventurer": "#89ddff",
    "enemy":      "#ff5370",
    "location":   "#c3e88d",
    "quest":      "#ffcb6b",
    "faction":    "#f78c6c",
    "item":       "#82aaff",
    "session":    "#b2ccd6",
    "encounter":  "#f07178",
}


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class Dashboard(Screen):
    BINDINGS = [
        Binding("n", "goto('npc')", "NPCs"),
        Binding("a", "goto('adventurer')", "Adventurers"),
        Binding("x", "goto('enemy')", "Enemies"),
        Binding("l", "goto('location')", "Locations"),
        Binding("q", "goto('quest')", "Quests"),
        Binding("f", "goto('faction')", "Factions"),
        Binding("i", "goto('item')", "Items"),
        Binding("s", "goto('session')", "Sessions"),
        Binding("c", "goto('encounter')", "Encounters"),
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

    async def on_mount(self):
        await self.refresh_cards()

    async def on_screen_resume(self):
        await self.refresh_cards()

    async def refresh_cards(self):
        counts = db.entity_counts()
        cards = self.query_one("#cards")
        await cards.remove_children()
        new_cards = [
            Button(
                f"[bold]{ENTITY_LABELS_PLURAL[type_]}[/bold]\n{counts.get(type_, 0)} entries",
                id=f"card-{type_}",
                classes="card",
            )
            for type_ in ENTITY_TYPES
        ]
        await cards.mount(*new_cards)

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
        self.label_plural = ENTITY_LABELS_PLURAL[type_]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Horizontal(
                Input(placeholder=f"Search {self.label_plural}...", id="search"),
                Button("+ Add", id="btn-add", variant="primary"),
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

def _format_sheet_lines(entity_type: str, raw_sheet: dict) -> list[str]:
    sheet = shm.normalize_sheet(raw_sheet)
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

    return lines


class EntityDetailScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("e", "edit", "Edit"),
        Binding("r", "add_rel", "Add Relation"),
        Binding("d", "del_rel", "Delete Relation"),
        Binding("c", "open_sheet", "Character Sheet"),
        Binding("k", "open_roll", "Roll Dice"),
        Binding("h", "make_hostile", "Make Hostile"),
        Binding("o", "open_combat", "Combat Tracker"),
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
            lines.extend(_format_sheet_lines(entity["type"], entity["fields"].get("sheet", {})))

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
        elif event.button.id == "btn-sheet":
            self.action_open_sheet()
        elif event.button.id == "btn-roll":
            self.action_open_roll()
        elif event.button.id == "btn-hostile":
            self.action_make_hostile()
        elif event.button.id == "btn-combat":
            self.action_open_combat()

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
        enemy_fields = {
            "creature_type": fields.get("race", ""),
            "cr": "",
            "alignment": fields.get("alignment", ""),
            "status": "Alive",
        }
        enemy_id = db.create_entity("enemy", f"{entity['name']} (Hostile)", enemy_fields, "")
        db.create_relationship(enemy_id, self.entity_id, "hostile form of", "")
        self.app.push_screen(EntityDetailScreen(enemy_id), callback=lambda _: self._render_detail())

    def action_open_combat(self):
        entity = db.get_entity(self.entity_id)
        if entity and entity["type"] == "encounter":
            self.app.push_screen(CombatTrackerScreen(self.entity_id), callback=lambda _: self._render_detail())


# ---------------------------------------------------------------------------
# Character Sheet
# ---------------------------------------------------------------------------

SKILL_LEVEL_OPTIONS = [("None", "none"), ("Proficient", "proficient"), ("Expertise", "expertise")]


class CharacterSheetScreen(Screen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "save", "Save"),
    ]

    def __init__(self, entity_id: int):
        super().__init__()
        self.entity_id = entity_id
        entity = db.get_entity(entity_id)
        self.entity_type = entity["type"]
        self.sheet = shm.normalize_sheet(entity["fields"].get("sheet", {}))
        self.pending_attacks: list[dict] = list(self.sheet["attacks"])
        self.pending_specials: list[dict] = list(self.sheet["special_abilities"])

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id="sheet-tabs"):
            with TabPane("Abilities", id="tab-abilities"):
                yield ScrollableContainer(Container(id="abilities-fields"), id="abilities-scroll")
            with TabPane("Combat", id="tab-combat"):
                yield ScrollableContainer(Container(id="combat-fields"), id="combat-scroll")
            with TabPane("Skills & Saves", id="tab-skills"):
                yield ScrollableContainer(Container(id="skills-fields"), id="skills-scroll")
            with TabPane("Attacks & Traits", id="tab-attacks"):
                yield ScrollableContainer(Container(id="attacks-fields"), id="attacks-scroll")
        yield Container(
            Button("Recalculate", id="btn-recalc", variant="primary"),
            Button("Save (Ctrl+S)", id="btn-save", variant="success"),
            Button("Cancel", id="btn-cancel", variant="default"),
            id="sheet-actions",
        )
        yield Footer()

    async def on_mount(self):
        entity = db.get_entity(self.entity_id)
        self.title = f"{entity['name']} - Character Sheet"
        await self._build_abilities_tab()
        await self._build_combat_tab()
        await self._build_skills_tab()
        await self._build_attacks_tab()
        self._refresh_computed_displays()

    # -- tab builders --------------------------------------------------

    async def _build_abilities_tab(self):
        container = self.query_one("#abilities-fields")
        rows = [
            Horizontal(
                Label(shm.ABILITY_LABELS[a], classes="ability-label"),
                Input(value=str(self.sheet["abilities"][a]), id=f"sheet-ability-{a}", classes="ability-input"),
                Static("+0", id=f"sheet-mod-{a}", classes="ability-mod"),
                classes="ability-row",
            )
            for a in shm.ABILITIES
        ]
        await container.mount(*rows)

    async def _build_combat_tab(self):
        container = self.query_one("#combat-fields")
        widgets = [
            Label("Armor Class"), Input(value=str(self.sheet["ac"]), id="sheet-ac"),
            Label("HP Max"), Input(value=str(self.sheet["hp_max"]), id="sheet-hp-max"),
            Label("HP Current"), Input(value=str(self.sheet["hp_current"]), id="sheet-hp-current"),
            Label("HP Temp"), Input(value=str(self.sheet["hp_temp"]), id="sheet-hp-temp"),
            Label("Hit Dice"), Input(value=self.sheet["hit_dice"], placeholder="e.g. 5d8+10", id="sheet-hit-dice"),
            Label("Speed (ft.)"), Input(value=str(self.sheet["speed"]), id="sheet-speed"),
        ]
        if self.entity_type == "enemy":
            widgets += [
                Label("Challenge Rating"), Input(value=self.sheet["cr"], placeholder="e.g. 1/2", id="sheet-cr"),
                Label("Creature Type"), Input(value=self.sheet["creature_type"], placeholder="e.g. Humanoid", id="sheet-creature-type"),
            ]
        else:
            widgets += [Label("Level"), Input(value=str(self.sheet["level"]), id="sheet-level")]
        widgets += [
            Label("Senses"), Input(value=self.sheet["senses"], placeholder="e.g. darkvision 60 ft.", id="sheet-senses"),
            Label("Languages"), Input(value=self.sheet["languages"], placeholder="e.g. Common, Elvish", id="sheet-languages"),
            Label("Proficiency Bonus (computed)"), Static("+2", id="sheet-prof-bonus"),
        ]
        await container.mount(*widgets)

    async def _build_skills_tab(self):
        container = self.query_one("#skills-fields")
        save_rows = [
            Horizontal(
                Label(shm.ABILITY_LABELS[a], classes="save-label"),
                Switch(value=a in self.sheet["saving_throw_proficiencies"], id=f"sheet-save-{a}"),
                Static("+0", id=f"sheet-save-bonus-{a}", classes="save-bonus"),
                classes="save-row",
            )
            for a in shm.ABILITIES
        ]
        skill_rows = [
            Horizontal(
                Label(f"{shm.SKILL_LABELS[s]} ({shm.SKILLS[s].upper()})", classes="skill-label"),
                Select(SKILL_LEVEL_OPTIONS, value=self.sheet["skill_proficiencies"].get(s, "none"), id=f"sheet-skill-{s}", allow_blank=False),
                Static("+0", id=f"sheet-skill-bonus-{s}", classes="skill-bonus"),
                classes="skill-row",
            )
            for s in shm.SKILLS
        ]
        await container.mount(
            Static("[bold]Saving Throws[/]"), *save_rows,
            Static("[bold]Skills[/]"), *skill_rows,
        )

    async def _build_attacks_tab(self):
        container = self.query_one("#attacks-fields")
        await container.mount(
            Static("[bold]Attacks[/]"),
            Horizontal(
                Input(placeholder="Name", id="attack-name"),
                Input(placeholder="To-Hit Bonus", id="attack-bonus"),
                Input(placeholder="Damage (e.g. 1d6+2)", id="attack-damage"),
                Input(placeholder="Damage Type", id="attack-damage-type"),
                id="attack-inputs",
            ),
            Horizontal(
                Button("+ Add Attack", id="btn-add-attack"),
                Button("Remove Selected", id="btn-remove-attack"),
                id="attack-actions",
            ),
            ListView(id="list-attacks"),
            Static("[bold]Resistances / Immunities / Vulnerabilities[/]"),
            Input(value=self.sheet["resistances"], placeholder="Resistances", id="sheet-resistances"),
            Input(value=self.sheet["immunities"], placeholder="Immunities", id="sheet-immunities"),
            Input(value=self.sheet["vulnerabilities"], placeholder="Vulnerabilities", id="sheet-vulnerabilities"),
            Static("[bold]Special Abilities[/]"),
            Horizontal(
                Input(placeholder="Name", id="special-name"),
                Input(placeholder="Description", id="special-desc"),
                id="special-inputs",
            ),
            Horizontal(
                Button("+ Add Special Ability", id="btn-add-special"),
                Button("Remove Selected", id="btn-remove-special"),
                id="special-actions",
            ),
            ListView(id="list-specials"),
        )
        self._refresh_attacks_list()
        self._refresh_specials_list()

    # -- pending attack/special list management ------------------------

    def _refresh_attacks_list(self):
        lv = self.query_one("#list-attacks", ListView)
        lv.clear()
        for atk in self.pending_attacks:
            bonus = shm.format_modifier(int(atk.get("bonus", 0) or 0))
            text = f"{atk.get('name', '?')} {bonus} to hit, {atk.get('damage', '')} {atk.get('damage_type', '')}".rstrip()
            lv.append(ListItem(Label(text)))

    def _refresh_specials_list(self):
        lv = self.query_one("#list-specials", ListView)
        lv.clear()
        for sa in self.pending_specials:
            lv.append(ListItem(Label(f"{sa.get('name', '?')}: {sa.get('description', '')}")))

    def _add_attack(self):
        name = self.query_one("#attack-name", Input).value.strip()
        if not name:
            return
        bonus_raw = self.query_one("#attack-bonus", Input).value.strip()
        try:
            bonus = int(bonus_raw) if bonus_raw else 0
        except ValueError:
            bonus = 0
        damage = self.query_one("#attack-damage", Input).value.strip()
        damage_type = self.query_one("#attack-damage-type", Input).value.strip()
        self.pending_attacks.append({"name": name, "bonus": bonus, "damage": damage, "damage_type": damage_type})
        for widget_id in ("#attack-name", "#attack-bonus", "#attack-damage", "#attack-damage-type"):
            self.query_one(widget_id, Input).value = ""
        self._refresh_attacks_list()

    def _remove_attack(self):
        lv = self.query_one("#list-attacks", ListView)
        if lv.index is not None and lv.index < len(self.pending_attacks):
            del self.pending_attacks[lv.index]
            self._refresh_attacks_list()

    def _add_special(self):
        name = self.query_one("#special-name", Input).value.strip()
        if not name:
            return
        desc = self.query_one("#special-desc", Input).value.strip()
        self.pending_specials.append({"name": name, "description": desc})
        self.query_one("#special-name", Input).value = ""
        self.query_one("#special-desc", Input).value = ""
        self._refresh_specials_list()

    def _remove_special(self):
        lv = self.query_one("#list-specials", ListView)
        if lv.index is not None and lv.index < len(self.pending_specials):
            del self.pending_specials[lv.index]
            self._refresh_specials_list()

    # -- collecting + computed display ----------------------------------

    def _to_int(self, widget_id: str, default: int = 0) -> int:
        raw = self.query_one(f"#{widget_id}", Input).value.strip()
        try:
            return int(raw) if raw else default
        except ValueError:
            return default

    def _to_text(self, widget_id: str) -> str:
        return self.query_one(f"#{widget_id}", Input).value.strip()

    def _collect_sheet_from_widgets(self) -> dict:
        abilities = {a: self._to_int(f"sheet-ability-{a}", 10) for a in shm.ABILITIES}
        saving_throw_proficiencies = [a for a in shm.ABILITIES if self.query_one(f"#sheet-save-{a}", Switch).value]

        skill_proficiencies = {}
        for s in shm.SKILLS:
            value = str(self.query_one(f"#sheet-skill-{s}", Select).value)
            if value != "none":
                skill_proficiencies[s] = value

        sheet = {
            "abilities": abilities,
            "ac": self._to_int("sheet-ac", 10),
            "hp_max": self._to_int("sheet-hp-max", 10),
            "hp_current": self._to_int("sheet-hp-current", 10),
            "hp_temp": self._to_int("sheet-hp-temp", 0),
            "hit_dice": self._to_text("sheet-hit-dice"),
            "speed": self._to_int("sheet-speed", 30),
            "saving_throw_proficiencies": saving_throw_proficiencies,
            "skill_proficiencies": skill_proficiencies,
            "senses": self._to_text("sheet-senses"),
            "languages": self._to_text("sheet-languages"),
            "resistances": self._to_text("sheet-resistances"),
            "immunities": self._to_text("sheet-immunities"),
            "vulnerabilities": self._to_text("sheet-vulnerabilities"),
            "attacks": list(self.pending_attacks),
            "special_abilities": list(self.pending_specials),
        }
        if self.entity_type == "enemy":
            sheet["cr"] = self._to_text("sheet-cr")
            sheet["creature_type"] = self._to_text("sheet-creature-type")
            sheet["level"] = self.sheet.get("level", 1)
        else:
            sheet["level"] = self._to_int("sheet-level", 1)
            sheet["cr"] = self.sheet.get("cr", "0")
            sheet["creature_type"] = self.sheet.get("creature_type", "")
        return sheet

    def _refresh_computed_displays(self):
        sheet = self._collect_sheet_from_widgets()
        pb = shm.proficiency_bonus(self.entity_type, sheet)

        for a in shm.ABILITIES:
            mod = shm.ability_modifier(sheet["abilities"][a])
            self.query_one(f"#sheet-mod-{a}", Static).update(shm.format_modifier(mod))
            self.query_one(f"#sheet-save-bonus-{a}", Static).update(
                shm.format_modifier(shm.saving_throw_bonus(sheet, a, pb))
            )
        for s in shm.SKILLS:
            self.query_one(f"#sheet-skill-bonus-{s}", Static).update(
                shm.format_modifier(shm.skill_bonus(sheet, s, pb))
            )
        self.query_one("#sheet-prof-bonus", Static).update(shm.format_modifier(pb))
        self.sheet = sheet

    # -- actions ----------------------------------------------------------

    def action_save(self):
        sheet = self._collect_sheet_from_widgets()
        entity = db.get_entity(self.entity_id)
        fields = dict(entity["fields"])
        fields["sheet"] = sheet
        db.update_entity(self.entity_id, entity["name"], fields, entity["notes"])
        self.dismiss(True)

    def action_cancel(self):
        self.dismiss(False)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-save":
            self.action_save()
        elif event.button.id == "btn-cancel":
            self.action_cancel()
        elif event.button.id == "btn-recalc":
            self._refresh_computed_displays()
        elif event.button.id == "btn-add-attack":
            self._add_attack()
        elif event.button.id == "btn-remove-attack":
            self._remove_attack()
        elif event.button.id == "btn-add-special":
            self._add_special()
        elif event.button.id == "btn-remove-special":
            self._remove_special()


# ---------------------------------------------------------------------------
# Roll Picker
# ---------------------------------------------------------------------------

class RollPickerScreen(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "Back")]

    HISTORY_LIMIT = 20

    def __init__(self, entity_id: int):
        super().__init__()
        self.entity_id = entity_id
        entity = db.get_entity(entity_id)
        self.entity_type = entity["type"]
        self.entity_name = entity["name"]
        self.sheet = shm.normalize_sheet(entity["fields"].get("sheet", {}))
        self.history: list[str] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id="roll-tabs"):
            with TabPane("Ability / Save", id="tab-roll-ability"):
                yield ScrollableContainer(Container(id="roll-ability-fields"), id="roll-ability-scroll")
            with TabPane("Skills", id="tab-roll-skill"):
                yield ScrollableContainer(Container(id="roll-skill-fields"), id="roll-skill-scroll")
            with TabPane("Attacks", id="tab-roll-attack"):
                yield ScrollableContainer(Container(id="roll-attack-fields"), id="roll-attack-scroll")
            with TabPane("Custom", id="tab-roll-custom"):
                yield ScrollableContainer(Container(id="roll-custom-fields"), id="roll-custom-scroll")
        yield Container(
            Static("Pick a roll above and press a button.", id="roll-result"),
            ListView(id="roll-history"),
            id="roll-output",
        )
        yield Footer()

    async def on_mount(self):
        self.title = f"{self.entity_name} - Roll Dice"
        await self._build_ability_tab()
        await self._build_skill_tab()
        await self._build_attack_tab()
        await self._build_custom_tab()

    # -- tab builders --------------------------------------------------

    async def _build_ability_tab(self):
        container = self.query_one("#roll-ability-fields")
        await container.mount(
            Label("Ability"),
            Select([(shm.ABILITY_LABELS[a], a) for a in shm.ABILITIES], id="roll-ability-select", allow_blank=False, value=shm.ABILITIES[0]),
            Horizontal(
                Switch(id="roll-ability-adv"), Label("Advantage"),
                Switch(id="roll-ability-dis"), Label("Disadvantage"),
                id="roll-ability-mode",
            ),
            Horizontal(
                Button("Roll Ability Check", id="btn-roll-ability-check"),
                Button("Roll Saving Throw", id="btn-roll-ability-save"),
                id="roll-ability-actions",
            ),
        )

    async def _build_skill_tab(self):
        container = self.query_one("#roll-skill-fields")
        await container.mount(
            Label("Skill"),
            Select([(shm.SKILL_LABELS[s], s) for s in shm.SKILLS], id="roll-skill-select", allow_blank=False, value=next(iter(shm.SKILLS))),
            Horizontal(
                Switch(id="roll-skill-adv"), Label("Advantage"),
                Switch(id="roll-skill-dis"), Label("Disadvantage"),
                id="roll-skill-mode",
            ),
            Button("Roll Skill Check", id="btn-roll-skill"),
        )

    async def _build_attack_tab(self):
        container = self.query_one("#roll-attack-fields")
        attacks = self.sheet["attacks"]
        if not attacks:
            await container.mount(Static("No attacks defined. Add some on the Character Sheet's Attacks & Traits tab."))
            return
        options = [(f"{a.get('name', '?')} ({shm.format_modifier(int(a.get('bonus', 0) or 0))})", str(i)) for i, a in enumerate(attacks)]
        await container.mount(
            Label("Attack"),
            Select(options, id="roll-attack-select", allow_blank=False, value="0"),
            Horizontal(
                Switch(id="roll-attack-adv"), Label("Advantage"),
                Switch(id="roll-attack-dis"), Label("Disadvantage"),
                id="roll-attack-mode",
            ),
            Horizontal(
                Button("Roll To-Hit", id="btn-roll-attack-hit"),
                Button("Roll Damage", id="btn-roll-attack-damage"),
                id="roll-attack-actions",
            ),
        )

    async def _build_custom_tab(self):
        container = self.query_one("#roll-custom-fields")
        await container.mount(
            Label("Dice Expression"),
            Input(placeholder="e.g. 2d6+3", id="roll-custom-input"),
            Button("Roll", id="btn-roll-custom"),
        )

    # -- rolling ----------------------------------------------------------

    def _record_result(self, label: str, result: dice.RollResult):
        text = f"{label}: {result.detail}"
        self.query_one("#roll-result", Static).update(f"[bold green]{text}[/]")
        self.history.insert(0, text)
        self.history = self.history[: self.HISTORY_LIMIT]
        lv = self.query_one("#roll-history", ListView)
        lv.clear()
        for entry in self.history:
            lv.append(ListItem(Label(entry)))

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id
        if bid == "btn-roll-ability-check":
            ability = str(self.query_one("#roll-ability-select", Select).value)
            adv = self.query_one("#roll-ability-adv", Switch).value
            dis = self.query_one("#roll-ability-dis", Switch).value
            result = dice.roll_ability_check(self.sheet, ability, advantage=adv, disadvantage=dis)
            self._record_result(f"{shm.ABILITY_LABELS[ability]} Check", result)
        elif bid == "btn-roll-ability-save":
            ability = str(self.query_one("#roll-ability-select", Select).value)
            adv = self.query_one("#roll-ability-adv", Switch).value
            dis = self.query_one("#roll-ability-dis", Switch).value
            result = dice.roll_saving_throw(self.sheet, self.entity_type, ability, advantage=adv, disadvantage=dis)
            self._record_result(f"{shm.ABILITY_LABELS[ability]} Save", result)
        elif bid == "btn-roll-skill":
            skill = str(self.query_one("#roll-skill-select", Select).value)
            adv = self.query_one("#roll-skill-adv", Switch).value
            dis = self.query_one("#roll-skill-dis", Switch).value
            result = dice.roll_skill_check(self.sheet, self.entity_type, skill, advantage=adv, disadvantage=dis)
            self._record_result(f"{shm.SKILL_LABELS[skill]} Check", result)
        elif bid == "btn-roll-attack-hit":
            attack = self.sheet["attacks"][int(self.query_one("#roll-attack-select", Select).value)]
            adv = self.query_one("#roll-attack-adv", Switch).value
            dis = self.query_one("#roll-attack-dis", Switch).value
            result = dice.roll_attack(attack, advantage=adv, disadvantage=dis)
            self._record_result(f"{attack.get('name', 'Attack')} To-Hit", result)
        elif bid == "btn-roll-attack-damage":
            attack = self.sheet["attacks"][int(self.query_one("#roll-attack-select", Select).value)]
            result = dice.roll_damage(attack)
            self._record_result(f"{attack.get('name', 'Attack')} Damage", result)
        elif bid == "btn-roll-custom":
            expr = self.query_one("#roll-custom-input", Input).value.strip()
            if not expr:
                return
            try:
                result = dice.roll(expr)
            except ValueError as ex:
                self.query_one("#roll-result", Static).update(f"[red]Error: {ex}[/red]")
                return
            self._record_result(expr, result)


# ---------------------------------------------------------------------------
# Combat Tracker
# ---------------------------------------------------------------------------

class CombatTrackerScreen(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "Back")]

    def __init__(self, entity_id: int):
        super().__init__()
        self.entity_id = entity_id
        entity = db.get_entity(entity_id)
        self.combat = cbt.normalize_combat(entity["fields"].get("combat", {}))

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id="combat-tabs"):
            with TabPane("Combatants", id="tab-combatants"):
                yield ScrollableContainer(Container(id="combatants-fields"), id="combatants-scroll")
            with TabPane("HP & Conditions", id="tab-hp-conditions"):
                yield ScrollableContainer(Container(id="hp-conditions-fields"), id="hp-conditions-scroll")
            with TabPane("Turn Controls", id="tab-turn-controls"):
                yield ScrollableContainer(Container(id="turn-controls-fields"), id="turn-controls-scroll")
        yield ScrollableContainer(Static(id="combat-summary"), id="combat-summary-scroll")
        yield Footer()

    async def on_mount(self):
        entity = db.get_entity(self.entity_id)
        self.title = f"{entity['name']} - Combat Tracker"
        await self._build_combatants_tab()
        await self._build_hp_conditions_tab()
        await self._build_turn_controls_tab()
        self._refresh_summary()

    # -- option helpers ---------------------------------------------------

    def _combatant_options(self):
        options = []
        for c in self.combat["combatants"]:
            entity = db.get_entity(c["entity_id"])
            if entity:
                options.append((f"{entity['name']} ({ENTITY_LABELS[entity['type']]})", str(c["entity_id"])))
        return options

    def _available_entity_options(self):
        in_combat = {c["entity_id"] for c in self.combat["combatants"]}
        return [
            (f"{e['name']} ({ENTITY_LABELS[e['type']]})", str(e["id"]))
            for e in db.list_entities()
            if e["type"] in shm.SHEET_ENTITY_TYPES and e["id"] not in in_combat
        ]

    def _set_options_preserving_selection(self, select: Select, options: list[tuple[str, str]]):
        previous = select.value
        select.set_options(options)
        if previous is not Select.NULL and any(previous == value for _, value in options):
            select.value = previous

    def _refresh_combatant_selects(self):
        options = self._combatant_options()
        for select_id in ("#sel-initiative-target", "#sel-remove-combatant", "#sel-hp-target"):
            self._set_options_preserving_selection(self.query_one(select_id, Select), options)
        self._set_options_preserving_selection(self.query_one("#sel-add-combatant", Select), self._available_entity_options())

    # -- tab builders -------------------------------------------------

    async def _build_combatants_tab(self):
        container = self.query_one("#combatants-fields")
        await container.mount(
            Label("Add Combatant"),
            Select(self._available_entity_options(), id="sel-add-combatant", prompt="Choose adventurer/enemy..."),
            Button("+ Add to Encounter", id="btn-add-combatant"),
            Label("Set Initiative"),
            Select(self._combatant_options(), id="sel-initiative-target", prompt="Choose combatant..."),
            Input(placeholder="Initiative score", id="input-initiative"),
            Horizontal(
                Button("Set Initiative", id="btn-set-initiative"),
                Button("Roll Initiative (DEX)", id="btn-roll-initiative"),
                id="initiative-actions",
            ),
            Label("Remove Combatant"),
            Select(self._combatant_options(), id="sel-remove-combatant", prompt="Choose combatant..."),
            Button("Remove from Encounter", id="btn-remove-combatant", variant="error"),
        )

    async def _build_hp_conditions_tab(self):
        container = self.query_one("#hp-conditions-fields")
        await container.mount(
            Label("Combatant"),
            Select(self._combatant_options(), id="sel-hp-target", prompt="Choose combatant..."),
            Label("HP Amount"),
            Input(placeholder="Amount", id="input-hp-amount"),
            Horizontal(
                Button("Apply Damage", id="btn-damage", variant="error"),
                Button("Apply Heal", id="btn-heal", variant="success"),
                id="hp-actions",
            ),
            Label("Add Condition"),
            Input(placeholder="Condition name (e.g. Prone)", id="input-condition-name"),
            Input(placeholder="Rounds remaining (blank = indefinite)", id="input-condition-rounds"),
            Button("Add Condition", id="btn-add-condition"),
            Label("Current Conditions (select one, then Remove)"),
            ListView(id="list-conditions"),
            Button("Remove Selected Condition", id="btn-remove-condition", variant="error"),
        )

    async def _build_turn_controls_tab(self):
        container = self.query_one("#turn-controls-fields")
        await container.mount(
            Button("Roll Initiative For All", id="btn-roll-all-initiative"),
            Button("Start Encounter (sort by initiative)", id="btn-start-encounter", variant="primary"),
            Horizontal(
                Button("Next Turn", id="btn-next-turn", variant="primary"),
                Button("Next Round", id="btn-next-round", variant="primary"),
                id="turn-advance-actions",
            ),
            Button("End Encounter", id="btn-end-encounter", variant="error"),
        )

    # -- persistence + summary --------------------------------------------

    def _persist(self):
        entity = db.get_entity(self.entity_id)
        fields = dict(entity["fields"])
        fields["combat"] = self.combat
        db.update_entity(self.entity_id, entity["name"], fields, entity["notes"])
        self._refresh_summary()
        self._refresh_combatant_selects()

    def _set_encounter_status(self, status: str):
        entity = db.get_entity(self.entity_id)
        fields = dict(entity["fields"])
        fields["status"] = status
        db.update_entity(self.entity_id, entity["name"], fields, entity["notes"])

    def _refresh_summary(self):
        lines = [
            f"[bold]Round {self.combat['round']}[/]  -  {'Started' if self.combat['started'] else 'Not Started'}",
            "",
        ]
        current = cbt.current_combatant(self.combat) if self.combat["started"] else None
        for c in self.combat["combatants"]:
            entity = db.get_entity(c["entity_id"])
            if not entity:
                continue
            sheet_data = shm.normalize_sheet(entity["fields"].get("sheet", {}))
            marker = "-> " if current and current["entity_id"] == c["entity_id"] else "   "
            color = PALETTE.get(entity["type"], "#ffffff")
            cond_str = ", ".join(
                f"{cd['name']}({cd['rounds_remaining'] if cd['rounds_remaining'] is not None else chr(0x221e)})"
                for cd in c["conditions"]
            ) or "none"
            lines.append(
                f"{marker}[bold {color}]{entity['name']}[/] - Init {c['initiative']} - "
                f"HP {sheet_data['hp_current']}/{sheet_data['hp_max']} - Conditions: {cond_str}"
            )
        if not self.combat["combatants"]:
            lines.append("[dim]No combatants yet. Add some on the Combatants tab.[/dim]")
        self.query_one("#combat-summary", Static).update("\n".join(lines))

    def _refresh_conditions_list(self, entity_id: int):
        lv = self.query_one("#list-conditions", ListView)
        lv.clear()
        target = next((c for c in self.combat["combatants"] if c["entity_id"] == entity_id), None)
        if not target:
            return
        for cond in target["conditions"]:
            suffix = f"{cond['rounds_remaining']} rounds left" if cond["rounds_remaining"] is not None else "indefinite"
            lv.append(ListItem(Label(f"{cond['name']} ({suffix})")))

    # -- actions ------------------------------------------------------

    def _add_combatant(self):
        sel = self.query_one("#sel-add-combatant", Select)
        if sel.value is Select.NULL:
            return
        self.combat = cbt.add_combatant(self.combat, int(str(sel.value)))
        self._persist()

    def _remove_combatant(self):
        sel = self.query_one("#sel-remove-combatant", Select)
        if sel.value is Select.NULL:
            return
        self.combat = cbt.remove_combatant(self.combat, int(str(sel.value)))
        self._persist()

    def _set_initiative(self):
        sel = self.query_one("#sel-initiative-target", Select)
        if sel.value is Select.NULL:
            return
        raw = self.query_one("#input-initiative", Input).value.strip()
        try:
            value = int(raw)
        except ValueError:
            return
        self.combat = cbt.set_initiative(self.combat, int(str(sel.value)), value)
        self._persist()

    def _roll_initiative_for_target(self):
        sel = self.query_one("#sel-initiative-target", Select)
        if sel.value is Select.NULL:
            return
        entity_id = int(str(sel.value))
        entity = db.get_entity(entity_id)
        if not entity:
            return
        sheet_data = shm.normalize_sheet(entity["fields"].get("sheet", {}))
        dex_mod = shm.ability_modifier(sheet_data["abilities"]["dex"])
        result = dice.roll_d20(dex_mod)
        self.combat = cbt.set_initiative(self.combat, entity_id, result.total)
        self._persist()

    def _roll_all_initiative(self):
        for c in list(self.combat["combatants"]):
            entity = db.get_entity(c["entity_id"])
            if not entity:
                continue
            sheet_data = shm.normalize_sheet(entity["fields"].get("sheet", {}))
            dex_mod = shm.ability_modifier(sheet_data["abilities"]["dex"])
            result = dice.roll_d20(dex_mod)
            self.combat = cbt.set_initiative(self.combat, c["entity_id"], result.total)
        self._persist()

    def _start_encounter(self):
        self.combat = cbt.start_encounter(self.combat)
        self._set_encounter_status("Active")
        self._persist()

    def _end_encounter(self):
        self._set_encounter_status("Complete")
        self._persist()

    def _apply_hp_delta(self, damage: bool):
        sel = self.query_one("#sel-hp-target", Select)
        if sel.value is Select.NULL:
            return
        raw = self.query_one("#input-hp-amount", Input).value.strip()
        try:
            amount = int(raw)
        except ValueError:
            return
        entity_id = int(str(sel.value))
        entity = db.get_entity(entity_id)
        if not entity:
            return
        sheet_data = shm.normalize_sheet(entity["fields"].get("sheet", {}))
        if damage:
            sheet_data["hp_current"] = cbt.apply_damage(sheet_data["hp_current"], amount)
        else:
            sheet_data["hp_current"] = cbt.apply_heal(sheet_data["hp_current"], sheet_data["hp_max"], amount)
        fields = dict(entity["fields"])
        fields["sheet"] = sheet_data
        db.update_entity(entity_id, entity["name"], fields, entity["notes"])
        self._refresh_summary()

    def _add_condition(self):
        sel = self.query_one("#sel-hp-target", Select)
        if sel.value is Select.NULL:
            return
        name = self.query_one("#input-condition-name", Input).value.strip()
        if not name:
            return
        rounds_raw = self.query_one("#input-condition-rounds", Input).value.strip()
        rounds = int(rounds_raw) if rounds_raw else None
        entity_id = int(str(sel.value))
        self.combat = cbt.add_condition(self.combat, entity_id, name, rounds)
        self.query_one("#input-condition-name", Input).value = ""
        self.query_one("#input-condition-rounds", Input).value = ""
        self._persist()
        self._refresh_conditions_list(entity_id)

    def _remove_condition(self):
        sel = self.query_one("#sel-hp-target", Select)
        if sel.value is Select.NULL:
            return
        lv = self.query_one("#list-conditions", ListView)
        if lv.index is None:
            return
        entity_id = int(str(sel.value))
        self.combat = cbt.remove_condition(self.combat, entity_id, lv.index)
        self._persist()
        self._refresh_conditions_list(entity_id)

    @on(Select.Changed, "#sel-hp-target")
    def _on_hp_target_changed(self, event: Select.Changed):
        if event.value is Select.NULL:
            return
        self._refresh_conditions_list(int(str(event.value)))

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id
        if bid == "btn-add-combatant":
            self._add_combatant()
        elif bid == "btn-remove-combatant":
            self._remove_combatant()
        elif bid == "btn-set-initiative":
            self._set_initiative()
        elif bid == "btn-roll-initiative":
            self._roll_initiative_for_target()
        elif bid == "btn-roll-all-initiative":
            self._roll_all_initiative()
        elif bid == "btn-start-encounter":
            self._start_encounter()
        elif bid == "btn-next-turn":
            self.combat = cbt.next_turn(self.combat)
            self._persist()
        elif bid == "btn-next-round":
            self.combat = cbt.next_round(self.combat)
            self._persist()
        elif bid == "btn-end-encounter":
            self._end_encounter()
        elif bid == "btn-damage":
            self._apply_hp_delta(damage=True)
        elif bid == "btn-heal":
            self._apply_hp_delta(damage=False)
        elif bid == "btn-add-condition":
            self._add_condition()
        elif bid == "btn-remove-condition":
            self._remove_condition()


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
