from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Input, Static, ListView, ListItem, Button, Label
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual import on

import srd
from screens.common import DismissableScreen, tint_border


class MonsterRefScreen(DismissableScreen):
    BINDINGS = [
        Binding("escape", "dismiss_screen", "Back"),
        Binding("ctrl+a", "add_to_campaign", "Add to Campaign"),
    ]

    def __init__(self):
        super().__init__()
        self._selected: dict | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            Vertical(
                Input(placeholder="Search by name or CR...", id="monster-search"),
                ListView(id="monster-list"),
                id="monster-left",
            ),
            ScrollableContainer(
                Static("Select a monster to view its stat block.", id="monster-detail"),
                id="monster-right",
            ),
            id="monster-split",
        )
        yield Horizontal(
            Button("Add to Campaign", id="btn-add-monster", variant="success"),
            Button("Back", id="btn-back", variant="default"),
            id="monster-actions",
        )
        yield Footer()

    async def on_mount(self):
        self.title = "SRD Monster Reference"
        tint_border(self.query_one("#monster-split"), "enemy")
        self._populate_list(srd.MONSTERS)
        self.query_one("#monster-search").focus()

    @on(Input.Changed, "#monster-search")
    def on_search(self, event: Input.Changed):
        results = srd.search(event.value)
        self._populate_list(results)

    def _populate_list(self, monsters: list[dict]):
        lv = self.query_one("#monster-list", ListView)
        lv.clear()
        for m in monsters:
            lv.append(ListItem(Label(f"{m['name']}  [dim](CR {m['cr']})[/dim]"), name=m["name"]))
        self._selected = monsters[0] if monsters else None
        if self._selected:
            self._show_detail(self._selected)
        else:
            self.query_one("#monster-detail", Static).update("[dim]No matches.[/dim]")

    @on(ListView.Highlighted, "#monster-list")
    def on_list_highlighted(self, event: ListView.Highlighted):
        if event.item is None:
            return
        name = event.item.name
        monster = srd.find(name) if name else None
        if monster:
            self._selected = monster
            self._show_detail(monster)

    def _show_detail(self, m: dict):
        lines = [
            f"[bold]{m['name']}[/bold]  CR {m['cr']}  --  {m['creature_type']}",
            f"AC {m['ac']}   HP {m['hp_max']}   Speed {m.get('speed', '30 ft.')}",
            "",
        ]
        ab = m["abilities"]
        lines.append(
            f"STR {ab['str']:2d}  DEX {ab['dex']:2d}  CON {ab['con']:2d}  "
            f"INT {ab['int']:2d}  WIS {ab['wis']:2d}  CHA {ab['cha']:2d}"
        )
        saves = m.get("saving_throw_proficiencies", [])
        if saves:
            lines.append(f"Saving Throws: {', '.join(s.upper() for s in saves)}")
        skills = m.get("skill_proficiencies", {})
        if skills:
            skill_str = ", ".join(f"{k.title()} ({v})" for k, v in skills.items())
            lines.append(f"Skills: {skill_str}")
        if m.get("resistances"):
            lines.append(f"Resistances: {m['resistances']}")
        if m.get("immunities"):
            lines.append(f"Immunities: {m['immunities']}")
        if m.get("vulnerabilities"):
            lines.append(f"Vulnerabilities: {m['vulnerabilities']}")
        senses = m.get("senses", "")
        if senses:
            lines.append(f"Senses: {senses}")
        langs = m.get("languages", "")
        if langs:
            lines.append(f"Languages: {langs}")
        lines.append("")
        attacks = m.get("attacks", [])
        if attacks:
            lines.append("[bold]Attacks[/bold]")
            for a in attacks:
                lines.append(f"  {a['name']}  {a['bonus']} to hit,  {a['damage']}")
        specials = m.get("special_abilities", [])
        if specials:
            lines.append("")
            lines.append("[bold]Special Abilities[/bold]")
            for s in specials:
                lines.append(f"  [italic]{s['name']}.[/italic] {s['description']}")
        self.query_one("#monster-detail", Static).update("\n".join(lines))

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-add-monster":
            self.action_add_to_campaign()
        else:
            self.action_dismiss_screen()

    def action_add_to_campaign(self):
        if not self._selected:
            self.app.notify("Select a monster first.", severity="warning")
            return
        from screens.wizard import WizardScreen
        prefill = srd.wizard_prefill(self._selected)
        self.app.push_screen(WizardScreen("enemy", "quick", prefill=prefill))
