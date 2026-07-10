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
import conditions as cnd
import encounter_balance as enc_bal
import effects as fx
import classes
from models import ENTITY_TYPES, ENTITY_LABELS, ENTITY_LABELS_PLURAL, ENTITY_SCHEMAS, RELATIONSHIP_TYPES

from screens.common import DismissableScreen, PALETTE, tint_border

class CombatTrackerScreen(DismissableScreen):
    BINDINGS = [Binding("escape", "dismiss_screen", "Back")]

    def __init__(self, entity_id: int):
        super().__init__()
        self.entity_id = entity_id
        entity = db.get_entity(entity_id)
        self.combat = cbt.normalize_combat(entity["fields"].get("combat", {}))
        self.round_notices: list[str] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id="combat-tabs"):
            with TabPane("Combatants", id="tab-combatants"):
                yield ScrollableContainer(Container(id="combatants-fields"), id="combatants-scroll")
            with TabPane("Attacks & HP", id="tab-hp-conditions"):
                yield ScrollableContainer(Container(id="hp-conditions-fields"), id="hp-conditions-scroll")
            with TabPane("Turn Controls", id="tab-turn-controls"):
                yield ScrollableContainer(Container(id="turn-controls-fields"), id="turn-controls-scroll")
        yield ScrollableContainer(Static(id="combat-summary"), id="combat-summary-scroll")
        yield Footer()

    async def on_mount(self):
        entity = db.get_entity(self.entity_id)
        self.title = f"{entity['name']} - Combat Tracker"
        tint_border(self.query_one("#combat-tabs"), "encounter")
        tint_border(self.query_one("#combat-summary-scroll"), "encounter")
        await self._build_combatants_tab()
        await self._build_hp_conditions_tab()
        await self._build_turn_controls_tab()
        self.query_one("#input-condition-custom").display = False
        self.query_one("#death-save-section").display = False
        self._refresh_summary()
        self._refresh_balance_readout()
        self._sync_attacker_to_current_turn()

    # -- option helpers ---------------------------------------------------

    def _combatant_options(self):
        options = []
        for c in self.combat["combatants"]:
            entity = db.get_entity(c["entity_id"])
            if entity:
                options.append((f"{entity['name']} ({ENTITY_LABELS[entity['type']]})", str(c["entity_id"])))
        return options

    def _available_entity_options(self):
        in_combat = {c["entity_id"] for c in self.combat["combatants"]}
        return [
            (f"{e['name']} ({ENTITY_LABELS[e['type']]})", str(e["id"]))
            for e in db.list_entities()
            if e["type"] in shm.SHEET_ENTITY_TYPES and e["id"] not in in_combat
        ]

    def _set_options_preserving_selection(self, select: Select, options: list[tuple[str, str]]):
        previous = select.value
        select.set_options(options)
        if previous is not Select.NULL and any(previous == value for _, value in options):
            select.value = previous

    def _refresh_combatant_selects(self):
        options = self._combatant_options()
        for select_id in ("#sel-initiative-target", "#sel-remove-combatant", "#sel-hp-target", "#sel-attack-attacker"):
            self._set_options_preserving_selection(self.query_one(select_id, Select), options)
        self._set_options_preserving_selection(self.query_one("#sel-add-combatant", Select), self._available_entity_options())
        self._refresh_attack_choices()

    # -- tab builders -------------------------------------------------

    async def _build_combatants_tab(self):
        container = self.query_one("#combatants-fields")
        await container.mount(
            Label("Add Combatant"),
            Select(self._available_entity_options(), id="sel-add-combatant", prompt="Choose adventurer/enemy..."),
            Button("+ Add to Encounter", id="btn-add-combatant"),
            Label("Set Initiative"),
            Select(self._combatant_options(), id="sel-initiative-target", prompt="Choose combatant..."),
            Input(placeholder="Initiative score", id="input-initiative"),
            Horizontal(
                Button("Set Initiative", id="btn-set-initiative"),
                Button("Roll Initiative (DEX)", id="btn-roll-initiative"),
                id="initiative-actions",
            ),
            Label("Remove Combatant"),
            Select(self._combatant_options(), id="sel-remove-combatant", prompt="Choose combatant..."),
            Button("Remove from Encounter", id="btn-remove-combatant", variant="error"),
            Static("", id="balance-readout"),
        )

    async def _build_hp_conditions_tab(self):
        container = self.query_one("#hp-conditions-fields")
        await container.mount(
            Label("Attacker (defaults to whoever's turn it is)"),
            Select(self._combatant_options(), id="sel-attack-attacker", prompt="Choose attacker..."),
            Label("Attack"),
            Select([], id="sel-attack-choice", prompt="Choose attack..."),
            Horizontal(
                Switch(id="attack-adv"), Label("Advantage"),
                Switch(id="attack-dis"), Label("Disadvantage"),
                id="attack-roll-mode",
            ),
            Horizontal(
                Button("Roll to Hit", id="btn-roll-attack-hit", variant="primary"),
                Button("Roll Damage", id="btn-roll-attack-damage", variant="warning"),
                id="attack-roll-actions",
            ),
            Static("Pick an attacker, an attack, and a target below, then roll.", id="attack-roll-result"),
            Label("Target / Combatant (also used for Apply Damage/Heal below)"),
            Select(self._combatant_options(), id="sel-hp-target", prompt="Choose combatant..."),
            Label("HP Amount"),
            Input(placeholder="Amount", id="input-hp-amount"),
            Horizontal(
                Button("Apply Damage", id="btn-damage", variant="error"),
                Button("Apply Heal", id="btn-heal", variant="success"),
                id="hp-actions",
            ),
            Label("Add Condition"),
            Select(
                [(name, name) for name in cnd.CONDITION_NAMES] + [("Custom...", "__custom__")],
                id="sel-condition-name",
                prompt="Choose condition...",
                allow_blank=True,
            ),
            Static("", id="condition-desc"),
            Input(placeholder="Custom condition name", id="input-condition-custom"),
            Input(placeholder="Rounds remaining (blank = indefinite)", id="input-condition-rounds"),
            Button("Add Condition", id="btn-add-condition"),
            Label("Current Conditions (select one, then Remove)"),
            ListView(id="list-conditions"),
            Button("Remove Selected Condition", id="btn-remove-condition", variant="error"),
            Container(
                Static("Death Saves", id="death-save-heading"),
                Static("", id="death-save-status"),
                Horizontal(
                    Button("+ Success", id="btn-ds-success", variant="success"),
                    Button("+ Failure", id="btn-ds-failure", variant="error"),
                    id="death-save-actions",
                ),
                id="death-save-section",
            ),
        )

    async def _build_turn_controls_tab(self):
        container = self.query_one("#turn-controls-fields")
        await container.mount(
            Button("Roll Initiative For All", id="btn-roll-all-initiative"),
            Button("Start Encounter (sort by initiative)", id="btn-start-encounter", variant="primary"),
            Horizontal(
                Button("Next Turn", id="btn-next-turn", variant="primary"),
                Button("Next Round", id="btn-next-round", variant="primary"),
                id="turn-advance-actions",
            ),
            Button("End Encounter", id="btn-end-encounter", variant="error"),
        )

    # -- persistence + summary --------------------------------------------

    def _persist(self):
        entity = db.get_entity(self.entity_id)
        fields = dict(entity["fields"])
        fields["combat"] = self.combat
        db.update_entity(self.entity_id, entity["name"], fields, entity["notes"])
        self._refresh_summary()
        self._refresh_combatant_selects()
        self._refresh_balance_readout()

    def _refresh_balance_readout(self):
        enemy_crs = []
        adventurer_levels = []
        for c in self.combat["combatants"]:
            entity = db.get_entity(c["entity_id"])
            if not entity:
                continue
            sheet_data = shm.normalize_sheet(entity["fields"].get("sheet", {}))
            if entity["type"] == "enemy":
                enemy_crs.append(str(sheet_data.get("cr", "")) or None)
            elif entity["type"] == "adventurer":
                try:
                    adventurer_levels.append(int(sheet_data.get("level", 1) or 1))
                except (TypeError, ValueError):
                    adventurer_levels.append(1)

        widget = self.query_one("#balance-readout", Static)
        if not self.combat["combatants"]:
            widget.update("")
            return

        result = enc_bal.calculate_difficulty(enemy_crs, adventurer_levels)
        difficulty = result["difficulty"]

        if difficulty == "Unknown":
            if not adventurer_levels:
                widget.update("[dim]Balance: add adventurers to calculate difficulty[/dim]")
            else:
                widget.update("[dim]Balance: no enemies with CR yet[/dim]")
            return

        color = {"Trivial": "#c3e88d", "Easy": "#c3e88d", "Medium": "#ffcb6b",
                 "Hard": "#f78c6c", "Deadly": "#ff5370"}.get(difficulty, "#ffffff")
        xp_str = f"{result['adjusted_xp']:,}"
        thresh = result["thresholds"]
        next_thresh = None
        if difficulty == "Trivial":
            next_thresh = f"Easy at {thresh['easy']:,}"
        elif difficulty == "Easy":
            next_thresh = f"Medium at {thresh['medium']:,}"
        elif difficulty == "Medium":
            next_thresh = f"Hard at {thresh['hard']:,}"
        elif difficulty == "Hard":
            next_thresh = f"Deadly at {thresh['deadly']:,}"

        line = f"Balance: [{color}]{difficulty}[/] ({xp_str} adj. XP"
        if result["multiplier"] != 1.0:
            line += f" x{result['multiplier']}"
        line += ")"
        if next_thresh:
            line += f"  --  next: {next_thresh}"
        if result["excluded_count"]:
            line += f"  [dim]({result['excluded_count']} enemy/enemies missing CR, excluded)[/dim]"

        widget.update(line)

    def _set_encounter_status(self, status: str):
        entity = db.get_entity(self.entity_id)
        fields = dict(entity["fields"])
        fields["status"] = status
        db.update_entity(self.entity_id, entity["name"], fields, entity["notes"])

    def _effective_sheet(self, entity: dict) -> dict:
        base_sheet = shm.normalize_sheet(entity["fields"].get("sheet", {}))
        return fx.apply_to_sheet(base_sheet, entity["fields"].get("active_effects", []))

    def _tick_combatant_effects(self):
        notices = []
        for c in self.combat["combatants"]:
            entity = db.get_entity(c["entity_id"])
            if not entity:
                continue
            kept, expired = fx.tick_effects(entity["fields"].get("active_effects", []))
            if expired:
                fields = dict(entity["fields"])
                fields["active_effects"] = kept
                db.update_entity(c["entity_id"], entity["name"], fields, entity["notes"])
                for effect in expired:
                    notices.append(f"{effect['source']} wore off on {entity['name']}")
        self.round_notices = notices

    def _refresh_summary(self):
        # Re-running start_encounter() once already started would silently
        # reset round/turn_index back to 1/0, discarding mid-fight progress.
        self.query_one("#btn-start-encounter", Button).disabled = self.combat["started"]
        lines = [
            f"[bold]Round {self.combat['round']}[/]  -  {'Started' if self.combat['started'] else 'Not Started'}",
            "",
        ]
        current = cbt.current_combatant(self.combat) if self.combat["started"] else None
        for c in self.combat["combatants"]:
            entity = db.get_entity(c["entity_id"])
            if not entity:
                continue
            sheet_data = self._effective_sheet(entity)
            marker = "-> " if current and current["entity_id"] == c["entity_id"] else "   "
            color = PALETTE.get(entity["type"], "#ffffff")
            cond_str = ", ".join(
                f"{cd['name']}({cd['rounds_remaining'] if cd['rounds_remaining'] is not None else chr(0x221e)})"
                for cd in c["conditions"]
            ) or "none"
            au = c.get("actions_used", {})
            used = [slot for slot, flag in (("A", "action"), ("BA", "bonus_action"), ("R", "reaction")) if au.get(flag)]
            used_str = f"  [dim](used: {', '.join(used)})[/]" if used else ""
            lines.append(
                f"{marker}[bold {color}]{entity['name']}[/] - Init {c['initiative']} - "
                f"HP {sheet_data['hp_current']}/{sheet_data['hp_max']} - AC {sheet_data['ac']} - "
                f"Conditions: {cond_str}{used_str}"
            )
        if not self.combat["combatants"]:
            lines.append("[dim]No combatants yet. Add some on the Combatants tab.[/dim]")
        if self.round_notices:
            lines.append("")
            lines.append("[bold yellow]Notices:[/]")
            for notice in self.round_notices:
                lines.append(f"  {notice}")
        self.query_one("#combat-summary", Static).update("\n".join(lines))

    def _refresh_conditions_list(self, entity_id: int):
        lv = self.query_one("#list-conditions", ListView)
        lv.clear()
        target = next((c for c in self.combat["combatants"] if c["entity_id"] == entity_id), None)
        if not target:
            return
        for cond in target["conditions"]:
            suffix = f"{cond['rounds_remaining']} rounds left" if cond["rounds_remaining"] is not None else "indefinite"
            lv.append(ListItem(Label(f"{cond['name']} ({suffix})")))

    # -- actions ------------------------------------------------------

    def _add_combatant(self):
        sel = self.query_one("#sel-add-combatant", Select)
        if sel.value is Select.NULL:
            return
        self.combat = cbt.add_combatant(self.combat, int(str(sel.value)))
        self._persist()

    def _remove_combatant(self):
        sel = self.query_one("#sel-remove-combatant", Select)
        if sel.value is Select.NULL:
            return
        self.combat = cbt.remove_combatant(self.combat, int(str(sel.value)))
        self._persist()

    def _set_initiative(self):
        sel = self.query_one("#sel-initiative-target", Select)
        if sel.value is Select.NULL:
            return
        raw = self.query_one("#input-initiative", Input).value.strip()
        try:
            value = int(raw)
        except ValueError:
            return
        self.combat = cbt.set_initiative(self.combat, int(str(sel.value)), value)
        self._persist()

    def _roll_initiative_for_target(self):
        sel = self.query_one("#sel-initiative-target", Select)
        if sel.value is Select.NULL:
            return
        entity_id = int(str(sel.value))
        entity = db.get_entity(entity_id)
        if not entity:
            return
        sheet_data = self._effective_sheet(entity)
        dex_mod = shm.ability_modifier(sheet_data["abilities"]["dex"])
        result = dice.roll_d20(dex_mod)
        self.combat = cbt.set_initiative(self.combat, entity_id, result.total)
        self._persist()

    def _roll_all_initiative(self):
        for c in list(self.combat["combatants"]):
            entity = db.get_entity(c["entity_id"])
            if not entity:
                continue
            sheet_data = self._effective_sheet(entity)
            dex_mod = shm.ability_modifier(sheet_data["abilities"]["dex"])
            result = dice.roll_d20(dex_mod)
            self.combat = cbt.set_initiative(self.combat, c["entity_id"], result.total)
        self._persist()

    # -- attack/damage rolling --------------------------------------------

    def _spell_save_dc_for(self, entity: dict, sheet: dict) -> int:
        return shm.spell_save_dc(sheet, entity["type"])

    def _spell_attack_bonus_for(self, entity: dict, sheet: dict) -> int:
        return shm.spell_attack_bonus(sheet, entity["type"])

    def _attack_options_for(self, entity_id: int):
        entity = db.get_entity(entity_id)
        if not entity:
            return []
        sheet_data = self._effective_sheet(entity)
        options = []
        for i, atk in enumerate(sheet_data["attacks"]):
            bonus = int(atk.get("bonus", 0) or 0)
            options.append((f"[W] {atk.get('name', '?')} ({shm.format_modifier(bonus)})", f"w:{i}"))
        for i, sp in enumerate(sheet_data["spells"]):
            lvl_label = "Cantrip" if sp["level"] == 0 else f"L{sp['level']}"
            sor = sp.get("save_or_attack", "none")
            if sor == "attack":
                bonus = self._spell_attack_bonus_for(entity, sheet_data)
                extra = shm.format_modifier(bonus)
            elif sor == "save":
                dc = self._spell_save_dc_for(entity, sheet_data)
                extra = f"DC {dc}"
            else:
                extra = "no roll"
            options.append((f"[S] {sp['name']} ({lvl_label}, {extra})", f"s:{i}"))
        return options

    def _refresh_attack_choices(self):
        attacker_sel = self.query_one("#sel-attack-attacker", Select)
        options = [] if attacker_sel.value is Select.NULL else self._attack_options_for(int(str(attacker_sel.value)))
        select = self.query_one("#sel-attack-choice", Select)
        self._set_options_preserving_selection(select, options)
        if select.value is Select.NULL and options:
            select.value = options[0][1]

    def _sync_attacker_to_current_turn(self):
        current = cbt.current_combatant(self.combat) if self.combat["started"] else None
        if current is None:
            return
        sel = self.query_one("#sel-attack-attacker", Select)
        entity_id_str = str(current["entity_id"])
        if any(value == entity_id_str for _, value in self._combatant_options()):
            sel.value = entity_id_str
        self._refresh_attack_choices()

    def _selected_attack(self):
        """Return (attacker_entity, action_dict) where action_dict has a '_type' key of 'weapon' or 'spell'."""
        attacker_sel = self.query_one("#sel-attack-attacker", Select)
        attack_sel = self.query_one("#sel-attack-choice", Select)
        if attacker_sel.value is Select.NULL or attack_sel.value is Select.NULL:
            return None, None
        attacker_entity = db.get_entity(int(str(attacker_sel.value)))
        if not attacker_entity:
            return None, None
        sheet_data = self._effective_sheet(attacker_entity)
        value = str(attack_sel.value)
        if value.startswith("s:"):
            index = int(value[2:])
            if index >= len(sheet_data["spells"]):
                return None, None
            return attacker_entity, {**sheet_data["spells"][index], "_type": "spell"}
        else:
            index = int(value[2:]) if value.startswith("w:") else int(value)
            if index >= len(sheet_data["attacks"]):
                return None, None
            return attacker_entity, {**sheet_data["attacks"][index], "_type": "weapon"}

    def _mark_attack_action_used(self, entity_id: int, action: dict):
        cost = action.get("action_cost", "action")
        if cost in ("action", "bonus_action", "reaction"):
            self.combat = cbt.mark_action_used(self.combat, entity_id, cost)
            self._persist()

    def _decrement_spell_slot(self, entity_id: int, level: int):
        if level == 0:
            return
        entity = db.get_entity(entity_id)
        if not entity:
            return
        sheet_data = shm.normalize_sheet(entity["fields"].get("sheet", {}))
        slot = sheet_data["spell_slots"].get(str(level), {"current": 0, "max": 0})
        remaining = slot["current"]
        if remaining > 0:
            sheet_data["spell_slots"][str(level)]["current"] = remaining - 1
            fields = dict(entity["fields"])
            fields["sheet"] = sheet_data
            db.update_entity(entity_id, entity["name"], fields, entity["notes"])
            self.app.notify(f"Level {level} slot used -- {remaining - 1}/{slot['max']} remaining")
        else:
            self.app.notify(f"No level {level} slots remaining!", severity="warning")

    def _roll_attack_to_hit(self):
        attacker_entity, action = self._selected_attack()
        if not action:
            return
        self._last_attack = action
        sheet_data = self._effective_sheet(attacker_entity)

        if action.get("_type") == "spell":
            sor = action.get("save_or_attack", "none")
            if sor == "save":
                dc = self._spell_save_dc_for(attacker_entity, sheet_data)
                save_ability = action.get("save_ability", "")
                ability_label = shm.ABILITY_LABELS.get(save_ability, save_ability.upper()) if save_ability else "?"
                self.query_one("#attack-roll-result", Static).update(
                    f"{attacker_entity['name']} casts {action['name']} -- {ability_label} Save DC {dc}"
                )
            elif sor == "attack":
                bonus = self._spell_attack_bonus_for(attacker_entity, sheet_data)
                adv = self.query_one("#attack-adv", Switch).value
                dis = self.query_one("#attack-dis", Switch).value
                result = dice.roll_attack({"bonus": str(bonus), "name": action["name"]}, advantage=adv, disadvantage=dis)
                text = f"{attacker_entity['name']} - {action['name']} spell attack: {result.detail}"
                target_sel = self.query_one("#sel-hp-target", Select)
                if target_sel.value is not Select.NULL:
                    target_entity = db.get_entity(int(str(target_sel.value)))
                    if target_entity:
                        target_ac = self._effective_sheet(target_entity)["ac"]
                        hit = result.total >= target_ac
                        tag = "[bold green]HIT[/]" if hit else "[bold red]MISS[/]"
                        text += f"  ->  {tag} (AC {target_ac})"
                self.query_one("#attack-roll-result", Static).update(text)
            else:
                self.query_one("#attack-roll-result", Static).update(
                    f"{attacker_entity['name']} uses {action['name']} (automatic / no roll)"
                )
            self._mark_attack_action_used(attacker_entity["id"], action)
            if action.get("level", 0) > 0:
                self._decrement_spell_slot(attacker_entity["id"], action["level"])
            return

        adv = self.query_one("#attack-adv", Switch).value
        dis = self.query_one("#attack-dis", Switch).value
        result = dice.roll_attack(action, advantage=adv, disadvantage=dis)
        text = f"{attacker_entity['name']} - {action.get('name', '?')} to-hit: {result.detail}"
        target_sel = self.query_one("#sel-hp-target", Select)
        if target_sel.value is not Select.NULL:
            target_entity = db.get_entity(int(str(target_sel.value)))
            if target_entity:
                target_ac = self._effective_sheet(target_entity)["ac"]
                hit = result.total >= target_ac
                tag = "[bold green]HIT[/]" if hit else "[bold red]MISS[/]"
                text += f"  ->  {tag} (AC {target_ac})"
        self.query_one("#attack-roll-result", Static).update(text)
        self._mark_attack_action_used(attacker_entity["id"], action)

    def _roll_attack_damage(self):
        action = getattr(self, "_last_attack", None)
        if not action:
            return
        if action.get("_type") == "spell":
            desc = action.get("description", "")
            self.query_one("#attack-roll-result", Static).update(
                f"{action['name']}: {desc}" if desc else f"{action['name']}: see spell description for effect"
            )
            return
        result = dice.roll_damage(action)
        self.query_one("#attack-roll-result", Static).update(f"{action.get('name', '?')} damage: {result.detail}")
        self.query_one("#input-hp-amount", Input).value = str(result.total)

    @on(Select.Changed, "#sel-condition-name")
    def _on_condition_name_changed(self, event: Select.Changed):
        custom_input = self.query_one("#input-condition-custom", Input)
        desc = self.query_one("#condition-desc", Static)
        if event.value is Select.NULL:
            custom_input.display = False
            desc.update("")
            return
        name = str(event.value)
        if name == "__custom__":
            custom_input.display = True
            desc.update("")
        else:
            custom_input.display = False
            desc.update(cnd.CONDITIONS.get(name, ""))

    @on(Select.Changed, "#sel-attack-attacker")
    def _on_attack_attacker_changed(self, event: Select.Changed):
        self._refresh_attack_choices()

    def _start_encounter(self):
        self.combat = cbt.start_encounter(self.combat)
        self._set_encounter_status("Active")
        self._persist()

    def _end_encounter(self):
        self._set_encounter_status("Complete")
        self._persist()

    def _apply_hp_delta(self, damage: bool):
        sel = self.query_one("#sel-hp-target", Select)
        if sel.value is Select.NULL:
            return
        raw = self.query_one("#input-hp-amount", Input).value.strip()
        try:
            amount = int(raw)
        except ValueError:
            return
        entity_id = int(str(sel.value))
        entity = db.get_entity(entity_id)
        if not entity:
            return
        sheet_data = shm.normalize_sheet(entity["fields"].get("sheet", {}))
        if damage:
            sheet_data["hp_current"] = cbt.apply_damage(sheet_data["hp_current"], amount)
        else:
            sheet_data["hp_current"] = cbt.apply_heal(sheet_data["hp_current"], sheet_data["hp_max"], amount)
        fields = dict(entity["fields"])
        fields["sheet"] = sheet_data
        db.update_entity(entity_id, entity["name"], fields, entity["notes"])
        self._refresh_summary()

    def _add_condition(self):
        target_sel = self.query_one("#sel-hp-target", Select)
        if target_sel.value is Select.NULL:
            return
        cond_sel = self.query_one("#sel-condition-name", Select)
        if cond_sel.value is Select.NULL:
            return
        if str(cond_sel.value) == "__custom__":
            name = self.query_one("#input-condition-custom", Input).value.strip()
        else:
            name = str(cond_sel.value)
        if not name:
            return
        rounds_raw = self.query_one("#input-condition-rounds", Input).value.strip()
        rounds = int(rounds_raw) if rounds_raw else None
        entity_id = int(str(target_sel.value))
        self.combat = cbt.add_condition(self.combat, entity_id, name, rounds)
        self.query_one("#input-condition-custom", Input).value = ""
        self.query_one("#input-condition-rounds", Input).value = ""
        self._persist()
        self._refresh_conditions_list(entity_id)

    def _refresh_death_save_section(self):
        sel = self.query_one("#sel-hp-target", Select)
        section = self.query_one("#death-save-section")
        if sel.value is Select.NULL:
            section.display = False
            return
        entity_id = int(str(sel.value))
        entity = db.get_entity(entity_id)
        if not entity or entity["type"] != "adventurer":
            section.display = False
            return
        sheet_data = self._effective_sheet(entity)
        if sheet_data["hp_current"] > 0:
            section.display = False
            return
        combatant = next((c for c in self.combat["combatants"] if c["entity_id"] == entity_id), None)
        if not combatant:
            section.display = False
            return
        saves = combatant["death_saves"]
        self.query_one("#death-save-heading", Static).update(f"Death Saves -- {entity['name']}")
        self.query_one("#death-save-status", Static).update(
            f"Successes: {saves['successes']}/3    Failures: {saves['failures']}/3"
        )
        section.display = True

    def _add_death_save(self, success: bool):
        sel = self.query_one("#sel-hp-target", Select)
        if sel.value is Select.NULL:
            return
        entity_id = int(str(sel.value))
        self.combat, resolution = cbt.add_death_save(self.combat, entity_id, success)
        if resolution == "stable":
            self.combat = cbt.add_condition(self.combat, entity_id, "Stable", None)
            self.combat = cbt.reset_death_saves(self.combat, entity_id)
        elif resolution == "dead":
            self.combat = cbt.add_condition(self.combat, entity_id, "Dead", None)
            self.combat = cbt.reset_death_saves(self.combat, entity_id)
        self._persist()
        self._refresh_death_save_section()
        self._refresh_conditions_list(entity_id)

    def _remove_condition(self):
        sel = self.query_one("#sel-hp-target", Select)
        if sel.value is Select.NULL:
            return
        lv = self.query_one("#list-conditions", ListView)
        if lv.index is None:
            return
        entity_id = int(str(sel.value))
        self.combat = cbt.remove_condition(self.combat, entity_id, lv.index)
        self._persist()
        self._refresh_conditions_list(entity_id)

    @on(Select.Changed, "#sel-hp-target")
    def _on_hp_target_changed(self, event: Select.Changed):
        if event.value is Select.NULL:
            self.query_one("#death-save-section").display = False
            return
        entity_id = int(str(event.value))
        self._refresh_conditions_list(entity_id)
        self._refresh_death_save_section()

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id
        if bid == "btn-add-combatant":
            self._add_combatant()
        elif bid == "btn-remove-combatant":
            self._remove_combatant()
        elif bid == "btn-set-initiative":
            self._set_initiative()
        elif bid == "btn-roll-initiative":
            self._roll_initiative_for_target()
        elif bid == "btn-roll-all-initiative":
            self._roll_all_initiative()
        elif bid == "btn-start-encounter":
            self._start_encounter()
            self._sync_attacker_to_current_turn()
        elif bid == "btn-next-turn":
            old_round = self.combat["round"]
            self.combat = cbt.next_turn(self.combat)
            if self.combat["round"] != old_round:
                self._tick_combatant_effects()
            self._persist()
            self._sync_attacker_to_current_turn()
        elif bid == "btn-next-round":
            old_round = self.combat["round"]
            self.combat = cbt.next_round(self.combat)
            if self.combat["round"] != old_round:
                self._tick_combatant_effects()
            self._persist()
            self._sync_attacker_to_current_turn()
        elif bid == "btn-end-encounter":
            self._end_encounter()
        elif bid == "btn-damage":
            self._apply_hp_delta(damage=True)
            self._refresh_death_save_section()
        elif bid == "btn-heal":
            self._apply_hp_delta(damage=False)
            self._refresh_death_save_section()
        elif bid == "btn-add-condition":
            self._add_condition()
        elif bid == "btn-remove-condition":
            self._remove_condition()
        elif bid == "btn-roll-attack-hit":
            self._roll_attack_to_hit()
        elif bid == "btn-roll-attack-damage":
            self._roll_attack_damage()
        elif bid == "btn-ds-success":
            self._add_death_save(success=True)
        elif bid == "btn-ds-failure":
            self._add_death_save(success=False)
