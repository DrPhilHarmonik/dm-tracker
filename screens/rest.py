from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Label, Button, Input, Static, ListView, ListItem
from textual.containers import Container, Horizontal, ScrollableContainer
from textual import on

import db
import rest as rst
import sheet as shm
from screens.common import DismissableScreen, PALETTE, tint_border


class RestScreen(DismissableScreen):
    BINDINGS = [Binding("escape", "dismiss_screen", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(
            Static("[bold]Long Rest[/]", classes="rest-section-heading"),
            Static("Restores all HP and spell slots for every active adventurer.", classes="rest-desc"),
            Button("Apply Long Rest to All", id="btn-long-rest", variant="primary"),
            Static("", id="long-rest-result", classes="rest-result"),
            Static("[bold]Short Rest[/]", classes="rest-section-heading"),
            Static("Spend hit dice to recover HP. Select a character and enter dice count.", classes="rest-desc"),
            Container(id="short-rest-roster"),
            id="rest-scroll",
        )
        yield Footer()

    async def on_mount(self):
        self.title = "Party Rest"
        tint_border(self.query_one("#rest-scroll"), "adventurer")
        await self._build_roster()

    async def _build_roster(self):
        roster = self.query_one("#short-rest-roster")
        await roster.remove_children()
        adventurers = rst.active_adventurers()
        if not adventurers:
            await roster.mount(Static("[dim]No active adventurers.[/dim]"))
            return
        for adv in adventurers:
            sheet = shm.normalize_sheet(adv["fields"].get("sheet", {}))
            import classes as cls_mod
            class_name = adv["fields"].get("class_name", "")
            sides = cls_mod.CLASS_HIT_DICE.get(class_name) or rst._hit_die_sides(sheet)
            level = sheet.get("level", 1)
            con_mod = shm.ability_modifier(sheet["abilities"].get("con", 10))
            hp_frac = f"{sheet['hp_current']}/{sheet['hp_max']}"
            mod_str = shm.format_modifier(con_mod) if con_mod != 0 else ""
            slots_str = _format_slots(sheet)
            await roster.mount(
                Container(
                    Horizontal(
                        Label(f"[bold]{adv['name']}[/bold]", classes="rest-pc-name"),
                        Static(f"HP {hp_frac}  AC {sheet['ac']}  d{sides}{mod_str}/die  Lv {level}",
                               classes="rest-pc-stats"),
                        classes="rest-pc-header",
                    ),
                    Static(slots_str, classes="rest-slots", id=f"rest-slots-{adv['id']}") if slots_str else Static(""),
                    Horizontal(
                        Input(value="1", id=f"rest-dice-{adv['id']}", classes="rest-dice-input"),
                        Label("hit dice"),
                        Button("Roll & Apply", id=f"rest-apply-{adv['id']}", variant="success"),
                        Static("", id=f"rest-result-{adv['id']}", classes="rest-result"),
                        id=f"rest-row-{adv['id']}",
                    ),
                    classes="rest-pc-block",
                    id=f"rest-pc-{adv['id']}",
                )
            )

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id or ""
        if bid == "btn-long-rest":
            self._apply_long_rest()
        elif bid.startswith("rest-apply-"):
            entity_id = int(bid.removeprefix("rest-apply-"))
            self._apply_short_rest(entity_id)

    def _apply_long_rest(self):
        adventurers = rst.active_adventurers()
        names = []
        for adv in adventurers:
            sheet = shm.normalize_sheet(adv["fields"].get("sheet", {}))
            new_sheet = rst.apply_long_rest(sheet)
            fields = dict(adv["fields"])
            fields["sheet"] = new_sheet
            db.update_entity(adv["id"], adv["name"], fields, adv["notes"])
            names.append(adv["name"])
        result = f"Long rest complete: {', '.join(names)} fully restored." if names else "No adventurers to rest."
        self.query_one("#long-rest-result", Static).update(f"[bold green]{result}[/]")
        self.app.notify("Long rest applied to all active adventurers")
        self.call_after_refresh(self._rebuild_roster_async)

    def _apply_short_rest(self, entity_id: int):
        try:
            count = int(self.query_one(f"#rest-dice-{entity_id}", Input).value.strip() or "1")
            count = max(1, count)
        except ValueError:
            count = 1
        adv = db.get_entity(entity_id)
        if not adv:
            return
        sheet = shm.normalize_sheet(adv["fields"].get("sheet", {}))
        gain, detail = rst.roll_hit_dice(sheet, count)
        new_sheet = rst.apply_short_rest(sheet, gain)
        fields = dict(adv["fields"])
        fields["sheet"] = new_sheet
        db.update_entity(entity_id, adv["name"], fields, adv["notes"])
        result_widget = self.query_one(f"#rest-result-{entity_id}", Static)
        new_hp = f"{new_sheet['hp_current']}/{new_sheet['hp_max']}"
        result_widget.update(f"[green]+{gain} HP ({detail}) -> {new_hp}[/green]")
        # Update the header stats line
        try:
            self.query_one(f"#rest-pc-{entity_id} .rest-pc-stats", Static).update(
                f"HP {new_hp}  AC {new_sheet['ac']}  d{rst._hit_die_sides(new_sheet)}"
                f"{shm.format_modifier(shm.ability_modifier(new_sheet['abilities'].get('con', 10)))}/die"
                f"  Lv {new_sheet.get('level', 1)}"
            )
        except Exception:
            pass

    async def _rebuild_roster_async(self):
        await self._build_roster()

    def call_after_refresh(self, fn):
        self.set_timer(0.1, fn)


def _format_slots(sheet: dict) -> str:
    parts = []
    for lvl in range(1, 10):
        slot = sheet.get("spell_slots", {}).get(str(lvl), {})
        cur = slot.get("current", 0)
        mx = slot.get("max", 0)
        if mx > 0:
            parts.append(f"L{lvl}: {cur}/{mx}")
    return "  ".join(parts) if parts else ""
