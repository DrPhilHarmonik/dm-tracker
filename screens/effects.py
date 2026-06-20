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

class EffectsScreen(DismissableScreen):
    BINDINGS = [Binding("escape", "dismiss_screen", "Back")]

    def __init__(self, entity_id: int):
        super().__init__()
        self.entity_id = entity_id
        entity = db.get_entity(entity_id)
        self.effects = fx.normalize_effects(entity["fields"].get("active_effects", []))

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(
            Container(
                Label("Source"),
                Input(placeholder="e.g. Potion of Giant Strength", id="input-effect-source"),
                Label("Stat"),
                Select(
                    [(fx.STAT_LABELS[s], s) for s in fx.MODIFIABLE_STATS],
                    id="sel-effect-stat", allow_blank=False, value=fx.MODIFIABLE_STATS[0],
                ),
                Label("Modifier (signed, e.g. 4 or -2)"),
                Input(placeholder="4", id="input-effect-modifier"),
                Label("Rounds Remaining (blank = indefinite)"),
                Input(placeholder="10", id="input-effect-rounds"),
                Button("+ Add Effect", id="btn-add-effect", variant="success"),
                Label("Current Effects (select one, then Remove)"),
                ListView(id="list-effects"),
                Button("Remove Selected", id="btn-remove-effect", variant="error"),
                id="effects-fields",
            ),
            id="effects-scroll",
        )
        yield Footer()

    def on_mount(self):
        entity = db.get_entity(self.entity_id)
        self.title = f"{entity['name']} - Active Effects"
        self._refresh_list()

    def _refresh_list(self):
        lv = self.query_one("#list-effects", ListView)
        lv.clear()
        for effect in self.effects:
            duration = f"{effect['rounds_remaining']} rounds left" if effect["rounds_remaining"] is not None else "indefinite"
            modifier = shm.format_modifier(effect["modifier"])
            lv.append(ListItem(Label(f"{effect['source']}: {modifier} {fx.STAT_LABELS[effect['stat']]} ({duration})")))

    def _persist(self):
        entity = db.get_entity(self.entity_id)
        fields = dict(entity["fields"])
        fields["active_effects"] = self.effects
        db.update_entity(self.entity_id, entity["name"], fields, entity["notes"])
        self._refresh_list()

    def _add_effect(self):
        source = self.query_one("#input-effect-source", Input).value.strip()
        if not source:
            return
        stat = str(self.query_one("#sel-effect-stat", Select).value)
        modifier_raw = self.query_one("#input-effect-modifier", Input).value.strip()
        try:
            modifier = int(modifier_raw)
        except ValueError:
            return
        rounds_raw = self.query_one("#input-effect-rounds", Input).value.strip()
        rounds = int(rounds_raw) if rounds_raw else None
        self.effects = fx.add_effect(self.effects, source, stat, modifier, rounds)
        for widget_id in ("#input-effect-source", "#input-effect-modifier", "#input-effect-rounds"):
            self.query_one(widget_id, Input).value = ""
        self._persist()

    def _remove_effect(self):
        lv = self.query_one("#list-effects", ListView)
        if lv.index is None:
            return
        self.effects = fx.remove_effect(self.effects, lv.index)
        self._persist()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-add-effect":
            self._add_effect()
        elif event.button.id == "btn-remove-effect":
            self._remove_effect()
