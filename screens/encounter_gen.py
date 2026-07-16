from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Label, Button, DataTable, Input, Select, Static
from textual.containers import Container, Horizontal, ScrollableContainer
from rich.text import Text

import db
import srd
import sheet as shm
import encounter_gen as gen
import encounter_balance as enc_bal
from screens.common import DismissableScreen, PALETTE

_DIFFICULTIES = ["Easy", "Medium", "Hard", "Deadly"]

_DIFF_COLORS = {
    "Easy": "#c3e88d",
    "Medium": "#ffcb6b",
    "Hard": "#f78c6c",
    "Deadly": "#ff5370",
    "Trivial": "#c3e88d",
    "Unknown": "#ffffff",
}


class EncounterGenScreen(DismissableScreen):
    BINDINGS = [
        Binding("escape", "dismiss_screen", "Back"),
        Binding("ctrl+g", "generate", "Generate"),
    ]

    def __init__(self):
        super().__init__()
        self._monsters: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(
            Container(
                Label("Party Size"),
                Input(value="4", id="input-party-size"),
                Label("Average Party Level"),
                Input(value="1", id="input-party-level"),
                Label("Difficulty"),
                Select(
                    [(d, d.lower()) for d in _DIFFICULTIES],
                    value="medium",
                    id="sel-difficulty",
                ),
                Horizontal(
                    Button("Generate", id="btn-generate", variant="primary"),
                    Button("Regenerate", id="btn-regenerate", variant="default"),
                    id="gen-actions",
                ),
                Static("", id="gen-summary"),
                id="gen-form",
            ),
            id="gen-form-scroll",
        )
        yield DataTable(id="gen-result-table", show_cursor=False)
        yield Horizontal(
            Button("Add All to Campaign", id="btn-add-all", variant="success"),
            Button("Back", id="btn-back", variant="default"),
            id="gen-footer-actions",
        )
        yield Footer()

    async def on_mount(self):
        self.title = "Encounter Generator"
        table = self.query_one("#gen-result-table", DataTable)
        table.add_columns("Monster", "CR", "Type", "HP", "AC", "XP")
        self.query_one("#btn-add-all", Button).disabled = True

    def _party_levels(self) -> list[int]:
        try:
            size = max(1, int(self.query_one("#input-party-size", Input).value.strip() or "4"))
        except ValueError:
            size = 4
        try:
            level = max(1, min(20, int(self.query_one("#input-party-level", Input).value.strip() or "1")))
        except ValueError:
            level = 1
        return [level] * size

    def _difficulty(self) -> str:
        sel = self.query_one("#sel-difficulty", Select)
        return str(sel.value) if sel.value is not Select.NULL else "medium"

    def _run_generate(self, seed: int | None = None):
        party_levels = self._party_levels()
        difficulty = self._difficulty()
        self._monsters = gen.generate(party_levels, difficulty, seed=seed)
        self._refresh_table()
        self._refresh_summary(party_levels)
        self.query_one("#btn-add-all", Button).disabled = not self._monsters

    def _refresh_table(self):
        table = self.query_one("#gen-result-table", DataTable)
        table.clear()
        for m in self._monsters:
            xp = enc_bal.cr_xp(m["cr"]) or 0
            cr_color = PALETTE.get("enemy", "#ff5370")
            table.add_row(
                Text(m["name"]),
                Text(m["cr"], style=cr_color),
                Text(m["creature_type"]),
                Text(str(m["hp_max"])),
                Text(str(m["ac"])),
                Text(f"{xp:,}"),
            )

    def _refresh_summary(self, party_levels: list[int]):
        widget = self.query_one("#gen-summary", Static)
        if not self._monsters:
            widget.update("[dim]No monsters generated yet.[/dim]")
            return
        info = gen.summary(self._monsters, party_levels)
        diff = info["difficulty"]
        color = _DIFF_COLORS.get(diff, "#ffffff")
        adj = info["adjusted_xp"]
        mult = info["multiplier"]
        thresholds = info["thresholds"]
        thresh_line = "  |  ".join(
            f"{k.capitalize()}: {v:,}" for k, v in thresholds.items()
        )
        line = (
            f"{len(self._monsters)} monster(s)  --  "
            f"[{color}]{diff}[/]  ({adj:,} adj. XP"
            + (f" x{mult}" if mult != 1.0 else "")
            + f")\n[dim]{thresh_line}[/dim]"
        )
        widget.update(line)

    def _add_all_to_campaign(self):
        if not self._monsters:
            return
        created = 0
        for m in self._monsters:
            prefill = srd.wizard_prefill(m)
            fields = {
                "cr": prefill["cr"],
                "creature_type": prefill["creature_type"],
                "ac": prefill["ac"],
                "hp_max": prefill["hp_max"],
                "resistances": prefill.get("resistances", ""),
                "immunities": prefill.get("immunities", ""),
                "vulnerabilities": prefill.get("vulnerabilities", ""),
                "sheet": shm.normalize_sheet({
                    "cr": prefill["cr"],
                    "abilities": prefill["abilities"],
                    "saving_throw_proficiencies": prefill.get("saving_throw_proficiencies", []),
                    "skill_proficiencies": prefill.get("skill_proficiencies", {}),
                    "attacks": prefill.get("attacks", []),
                    "special_abilities": prefill.get("special_abilities", []),
                    "ac": prefill["ac"],
                    "hp_max": prefill["hp_max"],
                }),
            }
            db.create_entity("enemy", m["name"], fields, "")
            created += 1
        self.app.notify(f"Added {created} enemy/enemies to campaign", severity="information")

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id
        if bid == "btn-generate":
            self._run_generate()
        elif bid == "btn-regenerate":
            self._run_generate()
        elif bid == "btn-add-all":
            self._add_all_to_campaign()
        elif bid == "btn-back":
            self.dismiss()
