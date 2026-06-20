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

class RollPickerScreen(DismissableScreen):
    BINDINGS = [Binding("escape", "dismiss_screen", "Back")]

    HISTORY_LIMIT = 20

    def __init__(self, entity_id: int):
        super().__init__()
        self.entity_id = entity_id
        entity = db.get_entity(entity_id)
        self.entity_type = entity["type"]
        self.entity_name = entity["name"]
        base_sheet = shm.normalize_sheet(entity["fields"].get("sheet", {}))
        self.sheet = fx.apply_to_sheet(base_sheet, entity["fields"].get("active_effects", []))
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
        tint_border(self.query_one("#roll-tabs"), self.entity_type)
        tint_border(self.query_one("#roll-output"), self.entity_type)
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
