from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, DataTable, Static
from textual.containers import Container

import db
import rest as rst
import sheet as shm
import combat as cbt
import effects as fx
from screens.common import DismissableScreen, tint_border


class PartyOverviewScreen(DismissableScreen):
    BINDINGS = [
        Binding("escape", "dismiss_screen", "Back"),
        Binding("r", "refresh_data", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("", id="overview-status"),
            DataTable(id="party-table", show_cursor=False),
            id="overview-wrap",
        )
        yield Footer()

    async def on_mount(self):
        self.title = "Party Overview"
        tint_border(self.query_one("#overview-wrap"), "adventurer")
        table = self.query_one("#party-table", DataTable)
        table.add_columns(
            "Name", "Class", "HP", "AC",
            "Conditions", "Spell Slots", "Active Effects",
        )
        self._load_data()

    async def on_screen_resume(self):
        self._load_data()

    def _load_data(self):
        table = self.query_one("#party-table", DataTable)
        table.clear()

        adventurers = rst.active_adventurers()
        if not adventurers:
            self.query_one("#overview-status", Static).update(
                "[dim]No active adventurers.[/dim]"
            )
            return
        self.query_one("#overview-status", Static).update("")

        conditions_by_id = _get_combat_conditions()

        for adv in adventurers:
            sheet = shm.normalize_sheet(adv["fields"].get("sheet", {}))
            active_effects = adv["fields"].get("active_effects", [])
            class_name = adv["fields"].get("class_name", "")

            hp_cur = sheet["hp_current"]
            hp_max = sheet["hp_max"]
            hp_text = _hp_cell(hp_cur, hp_max)

            conditions = conditions_by_id.get(adv["id"], [])
            cond_str = ", ".join(c["name"] for c in conditions) if conditions else "—"

            slots_str = _format_slots(sheet) or "—"

            effect_parts = []
            for e in fx.normalize_effects(active_effects):
                mod = shm.format_modifier(e["modifier"])
                label = fx.STAT_LABELS.get(e["stat"], e["stat"])
                rounds = f" ({e['rounds_remaining']}r)" if e.get("rounds_remaining") is not None else ""
                effect_parts.append(f"{e['source']} {mod} {label}{rounds}")
            effects_str = ", ".join(effect_parts) if effect_parts else "—"

            table.add_row(
                adv["name"],
                class_name or "—",
                hp_text,
                str(sheet["ac"]),
                cond_str,
                slots_str,
                effects_str,
            )

    def action_refresh_data(self):
        self._load_data()


# -- helpers ------------------------------------------------------------------

def _hp_cell(hp_cur: int, hp_max: int) -> Text:
    label = f"{hp_cur}/{hp_max}"
    if hp_max == 0:
        return Text(label, style="dim")
    pct = hp_cur / hp_max
    if hp_cur == 0:
        color = "bold red"
    elif pct > 0.5:
        color = "green"
    elif pct > 0.25:
        color = "yellow"
    else:
        color = "red"
    return Text(label, style=color)


def _get_combat_conditions() -> dict[int, list[dict]]:
    """Return {entity_id: [condition,...]} for combatants in any started encounter."""
    result: dict[int, list[dict]] = {}
    for enc in db.list_entities("encounter"):
        combat = cbt.normalize_combat(enc["fields"].get("combat"))
        if not combat["started"]:
            continue
        for combatant in combat["combatants"]:
            if combatant["conditions"]:
                result[combatant["entity_id"]] = combatant["conditions"]
    return result


def _format_slots(sheet: dict) -> str:
    parts = []
    for lvl in range(1, 10):
        slot = sheet.get("spell_slots", {}).get(str(lvl), {})
        cur = slot.get("current", 0)
        mx = slot.get("max", 0)
        if mx > 0:
            parts.append(f"L{lvl}:{cur}/{mx}")
    return "  ".join(parts)
