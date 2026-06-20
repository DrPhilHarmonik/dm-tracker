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

from screens.entities import EntityListScreen, GlobalSearchScreen
from screens.backup import ExportScreen, BackupScreen
from screens.common import DismissableScreen, PALETTE

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
                f"[bold {PALETTE[type_]}]{ENTITY_LABELS_PLURAL[type_]}[/]\n{counts.get(type_, 0)} entries",
                id=f"card-{type_}",
                classes="card",
            )
            for type_ in ENTITY_TYPES
        ]
        await cards.mount(*new_cards)
        for card in new_cards:
            card.styles.border = ("solid", PALETTE[card.id[5:]])

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
