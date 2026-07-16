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
import campaign_manager as cm
from models import ENTITY_TYPES, ENTITY_LABELS, ENTITY_LABELS_PLURAL, ENTITY_SCHEMAS, RELATIONSHIP_TYPES

from screens.entities import EntityListScreen, GlobalSearchScreen
from screens.backup import ExportScreen, BackupScreen
from screens.campaigns import CampaignSwitcherScreen
from screens.rest import RestScreen
from screens.party_overview import PartyOverviewScreen
from screens.award_xp import AwardXPScreen
from screens.monster_ref import MonsterRefScreen
from screens.encounter_gen import EncounterGenScreen
from screens.common import DismissableScreen, PALETTE

class Dashboard(Screen):
    BINDINGS = [
        Binding("n", "goto('npc')", "NPCs", show=False),
        Binding("a", "goto('adventurer')", "Adventurers", show=False),
        Binding("x", "goto('enemy')", "Enemies", show=False),
        Binding("l", "goto('location')", "Locations", show=False),
        Binding("q", "goto('quest')", "Quests", show=False),
        Binding("f", "goto('faction')", "Factions", show=False),
        Binding("i", "goto('item')", "Items", show=False),
        Binding("s", "goto('session')", "Sessions", show=False),
        Binding("c", "goto('encounter')", "Encounters", show=False),
        Binding("e", "export", "Export MD"),
        Binding("/", "search", "Search All"),
        Binding("b", "backup", "Backup/Restore"),
        Binding("ctrl+w", "campaigns", "Campaigns"),
        Binding("r", "rest", "Party Rest"),
        Binding("p", "party_overview", "Party Overview"),
        Binding("ctrl+x", "award_xp", "Award XP"),
        Binding("m", "monster_ref", "Monster Ref"),
        Binding("g", "encounter_gen", "Gen Encounter"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("", id="title"),
            Container(id="cards"),
            Horizontal(
                Button("Switch Campaign", id="btn-campaigns", variant="default"),
                Button("Party Rest", id="btn-rest", variant="warning"),
                Button("Party Overview", id="btn-party", variant="primary"),
                Button("Award XP", id="btn-xp", variant="warning"),
                Button("Monster Ref", id="btn-monster", variant="default"),
                Button("Gen Encounter", id="btn-gen", variant="warning"),
                Button("Export MD", id="btn-export", variant="success"),
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

    def _campaign_name(self) -> str:
        try:
            return cm.current_name()
        except Exception:
            return db.db_path().stem

    async def refresh_cards(self):
        self.query_one("#title", Static).update(
            f"[bold]DM Tracker[/bold]  --  {self._campaign_name()}"
        )
        counts = db.entity_counts()
        cards = self.query_one("#cards")
        await cards.remove_children()
        new_cards = [
            Button(
                f"[bold {PALETTE[type_]}]{ENTITY_LABELS_PLURAL[type_]}[/]\n"
                + (lambda n: f"{n} {'entry' if n == 1 else 'entries'}")(counts.get(type_, 0)),
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
        elif btn_id == "btn-campaigns":
            self.action_campaigns()
        elif btn_id == "btn-export":
            self.action_export()
        elif btn_id == "btn-search":
            self.action_search()
        elif btn_id == "btn-rest":
            self.action_rest()
        elif btn_id == "btn-party":
            self.action_party_overview()
        elif btn_id == "btn-xp":
            self.action_award_xp()
        elif btn_id == "btn-monster":
            self.action_monster_ref()
        elif btn_id == "btn-gen":
            self.action_encounter_gen()
        elif btn_id == "btn-backup":
            self.action_backup()

    def action_goto(self, type_: str):
        self.app.push_screen(EntityListScreen(type_))

    def action_export(self):
        self.app.push_screen(ExportScreen())

    def action_search(self):
        self.app.push_screen(GlobalSearchScreen())

    def action_rest(self):
        self.app.push_screen(RestScreen())

    def action_party_overview(self):
        self.app.push_screen(PartyOverviewScreen())

    def action_award_xp(self):
        self.app.push_screen(AwardXPScreen())

    def action_monster_ref(self):
        self.app.push_screen(MonsterRefScreen())

    def action_encounter_gen(self):
        self.app.push_screen(EncounterGenScreen())

    def action_backup(self):
        self.app.push_screen(BackupScreen())

    def action_campaigns(self):
        self.app.push_screen(CampaignSwitcherScreen())
