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

from screens.common import DismissableScreen, PALETTE, tint_border

class CombatTrackerScreen(DismissableScreen):
    BINDINGS = [Binding("escape", "dismiss_screen", "Back")]

    def __init__(self, entity_id: int):
        super().__init__()
        self.entity_id = entity_id
        entity = db.get_entity(entity_id)
        self.combat = cbt.normalize_combat(entity["fields"].get("combat", {}))
        self.round_notices: list[str] = []

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
        tint_border(self.query_one("#combat-tabs"), "encounter")
        tint_border(self.query_one("#combat-summary-scroll"), "encounter")
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

    def _effective_sheet(self, entity: dict) -> dict:
        base_sheet = shm.normalize_sheet(entity["fields"].get("sheet", {}))
        return fx.apply_to_sheet(base_sheet, entity["fields"].get("active_effects", []))

    def _tick_combatant_effects(self):
        notices = []
        for c in self.combat["combatants"]:
            entity = db.get_entity(c["entity_id"])
            if not entity:
                continue
            kept, expired = fx.tick_effects(entity["fields"].get("active_effects", []))
            if expired:
                fields = dict(entity["fields"])
                fields["active_effects"] = kept
                db.update_entity(c["entity_id"], entity["name"], fields, entity["notes"])
                for effect in expired:
                    notices.append(f"{effect['source']} wore off on {entity['name']}")
        self.round_notices = notices

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
            sheet_data = self._effective_sheet(entity)
            marker = "-> " if current and current["entity_id"] == c["entity_id"] else "   "
            color = PALETTE.get(entity["type"], "#ffffff")
            cond_str = ", ".join(
                f"{cd['name']}({cd['rounds_remaining'] if cd['rounds_remaining'] is not None else chr(0x221e)})"
                for cd in c["conditions"]
            ) or "none"
            lines.append(
                f"{marker}[bold {color}]{entity['name']}[/] - Init {c['initiative']} - "
                f"HP {sheet_data['hp_current']}/{sheet_data['hp_max']} - AC {sheet_data['ac']} - Conditions: {cond_str}"
            )
        if not self.combat["combatants"]:
            lines.append("[dim]No combatants yet. Add some on the Combatants tab.[/dim]")
        if self.round_notices:
            lines.append("")
            lines.append("[bold yellow]Notices:[/]")
            for notice in self.round_notices:
                lines.append(f"  {notice}")
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
        sheet_data = self._effective_sheet(entity)
        dex_mod = shm.ability_modifier(sheet_data["abilities"]["dex"])
        result = dice.roll_d20(dex_mod)
        self.combat = cbt.set_initiative(self.combat, entity_id, result.total)
        self._persist()

    def _roll_all_initiative(self):
        for c in list(self.combat["combatants"]):
            entity = db.get_entity(c["entity_id"])
            if not entity:
                continue
            sheet_data = self._effective_sheet(entity)
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
            old_round = self.combat["round"]
            self.combat = cbt.next_turn(self.combat)
            if self.combat["round"] != old_round:
                self._tick_combatant_effects()
            self._persist()
        elif bid == "btn-next-round":
            old_round = self.combat["round"]
            self.combat = cbt.next_round(self.combat)
            if self.combat["round"] != old_round:
                self._tick_combatant_effects()
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
