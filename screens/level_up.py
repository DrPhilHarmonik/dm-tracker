from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Button, Input, Static, Label
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual import on

import db
import sheet as shm
import levelup as lvu
from screens.common import DismissableScreen, tint_border


class LevelUpScreen(DismissableScreen):
    """Guided level-up workflow for a single adventurer."""

    BINDINGS = [
        Binding("escape", "dismiss_screen", "Cancel"),
        Binding("ctrl+s", "apply", "Apply"),
    ]

    def __init__(self, entity_id: int):
        super().__init__()
        self.entity_id = entity_id

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(
            Container(
                Static("", id="lu-heading"),
                Static("", id="lu-sub"),
                Static("[bold]HP Gain[/bold]", classes="lu-section-label"),
                Horizontal(
                    Label("HP gained this level:"),
                    Input(id="lu-hp-input", classes="lu-hp-input", placeholder="Enter HP gain"),
                    Button("Take Average", id="btn-average", variant="primary"),
                    id="lu-hp-row",
                ),
                Static("", id="lu-avg-hint"),
                Static("[bold]Spell Slots[/bold]", classes="lu-section-label"),
                Static("", id="lu-slots"),
                Static("[bold]Class Features[/bold]", classes="lu-section-label"),
                Static("", id="lu-features"),
                Horizontal(
                    Button("Apply Level Up (Ctrl+S)", id="btn-apply", variant="success"),
                    Button("Cancel", id="btn-cancel", variant="default"),
                    id="lu-actions",
                ),
                Static("", id="lu-result"),
                id="lu-wrap",
            ),
            id="lu-scroll",
        )
        yield Footer()

    async def on_mount(self):
        entity = db.get_entity(self.entity_id)
        self.title = f"Level Up -- {entity['name']}"
        tint_border(self.query_one("#lu-wrap"), "adventurer")

        fields = entity["fields"]
        self._sheet = shm.normalize_sheet(fields.get("sheet", {}))
        self._class_name = fields.get("class_name", "")
        old_level = int(self._sheet.get("level") or 1)
        self._new_level = min(20, old_level + 1)
        self._avg = lvu.average_hp_gain(self._class_name, self._con_modifier())

        self.query_one("#lu-heading", Static).update(
            f"[bold green]{entity['name']}[/]  Level {old_level} [bold]->[/bold] {self._new_level}"
        )
        self.query_one("#lu-sub", Static).update(
            f"Class: [cyan]{self._class_name or 'Unknown'}[/]  "
            f"Hit Die: [cyan]{_hit_die_label(self._class_name)}[/]  "
            f"CON modifier: [cyan]{shm.format_modifier(self._con_modifier())}[/]"
        )
        self.query_one("#lu-avg-hint", Static).update(
            f"[dim]Average result: {self._avg} hp  "
            f"({_hit_die_label(self._class_name)} / 2 + 1 + CON modifier)[/dim]"
        )
        self._refresh_slot_preview()
        self._refresh_features()

    def _con_modifier(self) -> int:
        con = int(self._sheet.get("abilities", {}).get("con", 10))
        return shm.ability_modifier(con)

    def _refresh_slot_preview(self):
        table = lvu.slot_table(self._class_name)
        if not table:
            self.query_one("#lu-slots", Static).update("[dim]No spell slots for this class.[/dim]")
            return

        new_maxes = table.get(self._new_level, {})
        old_maxes = table.get(self._new_level - 1, {})
        if self._new_level - 1 not in table:
            old_maxes = {}

        lines = []
        for lvl in range(1, 10):
            new_max = new_maxes.get(lvl, 0)
            old_max = old_maxes.get(lvl, 0)
            if new_max == 0 and old_max == 0:
                continue
            if new_max > old_max:
                lines.append(f"  Level {lvl}: {old_max} [bold green]->[/bold green] {new_max} slots")
            else:
                lines.append(f"  Level {lvl}: {new_max} slots")
        if not lines:
            self.query_one("#lu-slots", Static).update("[dim]No slot changes at this level.[/dim]")
        else:
            self.query_one("#lu-slots", Static).update("\n".join(lines))

    def _refresh_features(self):
        features = lvu.features_at_level(self._class_name, self._new_level)
        if features and features != "--" and features != "-":
            self.query_one("#lu-features", Static).update(
                f"  [bold cyan]{features}[/bold cyan]\n"
                "[dim]  (Reference only -- DM applies these to the character.)[/dim]"
            )
        else:
            self.query_one("#lu-features", Static).update("[dim]  No major new features at this level.[/dim]")

    @on(Button.Pressed, "#btn-average")
    def fill_average(self):
        self.query_one("#lu-hp-input", Input).value = str(self._avg)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-apply":
            self.action_apply()
        elif event.button.id == "btn-cancel":
            self.action_dismiss_screen()

    def action_apply(self):
        raw = self.query_one("#lu-hp-input", Input).value.strip()
        try:
            hp_gain = int(raw)
        except ValueError:
            self.query_one("#lu-result", Static).update(
                "[red]Enter a numeric HP gain (or use 'Take Average').[/red]"
            )
            return
        if hp_gain < 1:
            self.query_one("#lu-result", Static).update(
                "[red]HP gain must be at least 1.[/red]"
            )
            return

        entity = db.get_entity(self.entity_id)
        fields = dict(entity["fields"])
        new_sheet = lvu.apply_level_up(fields.get("sheet", {}), self._class_name, hp_gain)
        fields["sheet"] = new_sheet
        fields["level"] = str(new_sheet["level"])
        db.update_entity(self.entity_id, entity["name"], fields, entity["notes"])

        self.app.notify(
            f"{entity['name']} is now level {new_sheet['level']}!",
            severity="information",
        )
        self.dismiss(True)


# -- helpers ------------------------------------------------------------------

def _hit_die_label(class_name: str) -> str:
    import classes as cls_mod
    die = cls_mod.CLASS_HIT_DICE.get(class_name, 8)
    return f"d{die}"
