from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Label, Button, Input, Static, ListView, ListItem
from textual.containers import Container, Horizontal, ScrollableContainer
from textual import on

import db
import rest as rst
import xp as xpm
from screens.common import DismissableScreen, tint_border


class AwardXPScreen(DismissableScreen):
    BINDINGS = [Binding("escape", "dismiss_screen", "Cancel")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("[bold]Award Experience Points[/]", id="xp-heading"),
            Horizontal(
                Label("Total XP earned:"),
                Input(value="0", id="xp-input", classes="xp-amount-input"),
                id="xp-input-row",
            ),
            Static("", id="xp-split-label"),
            Static("[bold]Active adventurers[/]", id="xp-roster-heading"),
            ScrollableContainer(ListView(id="xp-roster"), id="xp-roster-scroll"),
            Horizontal(
                Button("Award XP", id="btn-award", variant="success"),
                Button("Cancel", id="btn-cancel", variant="default"),
                id="xp-actions",
            ),
            Static("", id="xp-result"),
            id="xp-wrap",
        )
        yield Footer()

    async def on_mount(self):
        self.title = "Award XP"
        tint_border(self.query_one("#xp-wrap"), "adventurer")
        self._adventurers = rst.active_adventurers()
        self._rebuild_roster()
        self._update_split_label()

    @on(Input.Changed, "#xp-input")
    def on_xp_changed(self, event: Input.Changed):
        self._update_split_label()

    def _update_split_label(self):
        total = self._parse_xp()
        n = len(self._adventurers)
        per_pc = xpm.split_xp(total, n)
        if n == 0:
            msg = "[dim]No active adventurers to award XP to.[/dim]"
        else:
            msg = f"[bold cyan]{per_pc:,}[/bold cyan] XP per PC  ({n} adventurers,  {total:,} total)"
        self.query_one("#xp-split-label", Static).update(msg)

    def _rebuild_roster(self):
        lv = self.query_one("#xp-roster", ListView)
        lv.clear()
        for adv in self._adventurers:
            current_xp = int(adv["fields"].get("xp") or 0)
            sheet_level = int(adv["fields"].get("level") or adv["fields"].get("sheet", {}).get("level") or 1)
            next_thresh = xpm.xp_for_next_level(sheet_level)
            if next_thresh is None:
                xp_str = f"{current_xp:,} XP  (Lv 20 -- max)"
            else:
                xp_str = f"{current_xp:,} / {next_thresh:,} XP  (Lv {sheet_level})"
            lv.append(ListItem(Label(f"{adv['name']}  --  {xp_str}")))

    def _parse_xp(self) -> int:
        try:
            return max(0, int(self.query_one("#xp-input", Input).value.strip() or "0"))
        except ValueError:
            return 0

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-award":
            self._do_award()
        else:
            self.action_dismiss_screen()

    def _do_award(self):
        total = self._parse_xp()
        if total <= 0:
            self.query_one("#xp-result", Static).update("[red]Enter a positive XP amount.[/red]")
            return
        n = len(self._adventurers)
        per_pc = xpm.split_xp(total, n)
        if per_pc <= 0:
            self.query_one("#xp-result", Static).update("[red]Not enough XP to split.[/red]")
            return

        level_ups = []
        for adv in self._adventurers:
            fields = dict(adv["fields"])
            old_xp = fields.get("xp", 0)
            new_xp = old_xp + per_pc
            fields["xp"] = new_xp
            db.update_entity(adv["id"], adv["name"], fields, adv["notes"])
            sheet_level = int(fields.get("level") or fields.get("sheet", {}).get("level") or 1)
            if xpm.should_level_up(new_xp, sheet_level):
                level_ups.append(adv["name"])

        msg = f"[green]Awarded {per_pc:,} XP to each of {n} adventurers.[/green]"
        if level_ups:
            msg += f"\n[bold yellow]Level up ready: {', '.join(level_ups)}![/bold yellow]"
        self.query_one("#xp-result", Static).update(msg)
        self.app.notify(f"XP awarded: {per_pc:,} each")

        # Refresh the roster to show updated totals
        self._adventurers = rst.active_adventurers()
        self._rebuild_roster()
        self._update_split_label()
