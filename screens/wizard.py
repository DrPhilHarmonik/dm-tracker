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

from screens.common import DismissableScreen, PALETTE, schema_choices
from screens.sheet import SKILL_LEVEL_OPTIONS

class WizardScreen(DismissableScreen):
    """Guided multi-step character creation.

    NPCs only ever get a single "basic info" step since they carry no
    stat block. Adventurers and Enemies walk Basic Info -> Class/CR ->
    Standard Array ability scores -> (advanced mode only: Skills & Saves,
    Attacks & Traits) -> Review & Create.
    """

    BINDINGS = [Binding("escape", "dismiss_screen", "Back")]

    def __init__(self, entity_type: str, mode: str = "quick", prefill: dict | None = None, link_to_npc_id: int | None = None):
        super().__init__()
        self.entity_type = entity_type
        self.mode = mode
        self.link_to_npc_id = link_to_npc_id
        self.data = {
            "name": "", "race": "", "alignment": "", "role": "", "status": "", "location": "",
            "class_name": classes.CLASSES[0], "level": 1, "cr": "0", "creature_type": "",
            "abilities": dict(zip(shm.ABILITIES, shm.STANDARD_ARRAY)),
            "saving_throw_proficiencies": [],
            "skill_proficiencies": {},
            "attacks": [],
            "special_abilities": [],
            "resistances": "", "immunities": "", "vulnerabilities": "",
            "ac": None, "hp_max": None,
        }
        if prefill:
            self.data.update(prefill)
        self.pending_attacks: list[dict] = list(self.data["attacks"])
        self.pending_specials: list[dict] = list(self.data["special_abilities"])
        self.steps = self._build_steps()
        self.step_index = 0

    def _build_steps(self) -> list[str]:
        if self.entity_type == "npc":
            return ["basic_npc", "review"]
        steps = ["basic", "class_or_cr", "abilities"]
        if self.mode == "advanced":
            steps += ["skills_saves", "attacks_traits"]
        steps.append("review")
        return steps

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(Container(id="wizard-step"), id="wizard-scroll")
        yield Container(
            Static("", id="wizard-error"),
            Horizontal(
                Button("< Back", id="btn-wiz-back"),
                Button("Next >", id="btn-wiz-next", variant="primary"),
                id="wizard-nav",
            ),
            id="wizard-actions",
        )
        yield Footer()

    async def on_mount(self):
        mode_label = "Quick" if self.mode == "quick" else "Advanced"
        self.title = f"Create {ENTITY_LABELS[self.entity_type]} ({mode_label} Wizard)"
        await self._render_step()

    # -- navigation -------------------------------------------------------

    async def _render_step(self):
        container = self.query_one("#wizard-step")
        await container.remove_children()
        step = self.steps[self.step_index]
        await getattr(self, f"_build_step_{step}")(container)
        self.query_one("#btn-wiz-back", Button).disabled = self.step_index == 0
        self.query_one("#btn-wiz-next", Button).label = "Create Character" if step == "review" else "Next >"
        self.query_one("#wizard-error", Static).update("")

    async def _go_back(self):
        if self.step_index == 0:
            return
        self.step_index -= 1
        await self._render_step()

    async def _go_next(self):
        step = self.steps[self.step_index]
        collector = getattr(self, f"_collect_step_{step}", None)
        if collector:
            error = collector()
            if error:
                self.query_one("#wizard-error", Static).update(f"[red]{error}[/red]")
                return
        if step == "review":
            self._create_entity()
            return
        self.step_index += 1
        await self._render_step()

    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-wiz-back":
            await self._go_back()
        elif event.button.id == "btn-wiz-next":
            await self._go_next()
        elif event.button.id == "btn-wiz-reset-array":
            self._reset_ability_inputs_to_standard_array()
        elif event.button.id == "btn-wiz-add-attack":
            self._add_attack()
        elif event.button.id == "btn-wiz-remove-attack":
            self._remove_attack()
        elif event.button.id == "btn-wiz-add-special":
            self._add_special()
        elif event.button.id == "btn-wiz-remove-special":
            self._remove_special()

    # -- step builders ------------------------------------------------

    async def _build_step_basic_npc(self, container):
        alignment_choices = schema_choices("npc", "alignment")
        status_choices = schema_choices("npc", "status")
        await container.mount(
            Static("[bold]Basic Info[/]"),
            Label("Name"), Input(value=self.data["name"], id="wiz-name"),
            Label("Race"), Input(value=self.data["race"], id="wiz-race"),
            Label("Role / Title"), Input(value=self.data["role"], id="wiz-role"),
            Label("Alignment"),
            Select([(a, a) for a in alignment_choices], id="wiz-alignment",
                   value=self.data["alignment"] or Select.NULL, allow_blank=True, prompt="Select alignment..."),
            Label("Status"),
            Select([(s, s) for s in status_choices], id="wiz-status",
                    value=self.data["status"] or Select.NULL, allow_blank=True, prompt="Select status..."),
            Label("Current Location"), Input(value=self.data["location"], id="wiz-location"),
        )

    async def _build_step_basic(self, container):
        widgets = [
            Static("[bold]Basic Info[/]"),
            Label("Name"), Input(value=self.data["name"], id="wiz-name"),
        ]
        if self.entity_type == "adventurer":
            widgets += [Label("Race"), Input(value=self.data["race"], id="wiz-race")]
        alignment_choices = schema_choices(self.entity_type, "alignment")
        widgets += [
            Label("Alignment"),
            Select([(a, a) for a in alignment_choices], id="wiz-alignment",
                   value=self.data["alignment"] or Select.NULL, allow_blank=True, prompt="Select alignment..."),
        ]
        await container.mount(*widgets)

    async def _build_step_class_or_cr(self, container):
        if self.entity_type == "adventurer":
            await container.mount(
                Static("[bold]Class & Level[/]"),
                Label("Class"),
                Select([(c, c) for c in classes.CLASSES], id="wiz-class", allow_blank=False, value=self.data["class_name"]),
                Label("Level"),
                Input(value=str(self.data["level"]), id="wiz-level"),
            )
        else:
            await container.mount(
                Static("[bold]Challenge Rating[/]"),
                Label("Creature Type"),
                Input(value=self.data["creature_type"], placeholder="e.g. Humanoid", id="wiz-creature-type"),
                Label("Challenge Rating"),
                Input(value=self.data["cr"], placeholder="e.g. 1/2", id="wiz-cr"),
            )

    async def _build_step_abilities(self, container):
        rows = []
        for a in shm.ABILITIES:
            rows.append(Horizontal(
                Label(shm.ABILITY_LABELS[a], classes="ability-label"),
                Input(value=str(self.data["abilities"][a]), id=f"wiz-ability-{a}", classes="ability-input"),
                classes="ability-row",
            ))
        await container.mount(
            Static(f"[bold]Ability Scores[/] - assign the Standard Array {shm.STANDARD_ARRAY}"),
            *rows,
            Button("Reset to Standard Array Order", id="btn-wiz-reset-array"),
        )

    async def _build_step_skills_saves(self, container):
        save_rows = [
            Horizontal(
                Label(shm.ABILITY_LABELS[a], classes="save-label"),
                Switch(value=a in self.data["saving_throw_proficiencies"], id=f"wiz-save-{a}"),
                classes="save-row",
            )
            for a in shm.ABILITIES
        ]
        skill_rows = [
            Horizontal(
                Label(f"{shm.SKILL_LABELS[s]} ({shm.SKILLS[s].upper()})", classes="skill-label"),
                Select(SKILL_LEVEL_OPTIONS, value=self.data["skill_proficiencies"].get(s, "none"), id=f"wiz-skill-{s}", allow_blank=False),
                classes="skill-row",
            )
            for s in shm.SKILLS
        ]
        await container.mount(
            Static("[bold]Saving Throws[/] (suggested by class, editable)" if self.entity_type == "adventurer" else "[bold]Saving Throws[/]"),
            *save_rows,
            Static("[bold]Skills[/]"),
            *skill_rows,
        )

    async def _build_step_attacks_traits(self, container):
        await container.mount(
            Static("[bold]Attacks[/]"),
            Horizontal(
                Input(placeholder="Name", id="wiz-attack-name"),
                Input(placeholder="To-Hit Bonus", id="wiz-attack-bonus"),
                Input(placeholder="Damage (e.g. 1d6+2)", id="wiz-attack-damage"),
                Input(placeholder="Damage Type", id="wiz-attack-damage-type"),
                id="wiz-attack-inputs",
            ),
            Horizontal(
                Button("+ Add Attack", id="btn-wiz-add-attack"),
                Button("Remove Selected", id="btn-wiz-remove-attack"),
                id="wiz-attack-actions",
            ),
            ListView(id="wiz-list-attacks"),
            Static("[bold]Resistances / Immunities / Vulnerabilities[/]"),
            Input(value=self.data["resistances"], placeholder="Resistances", id="wiz-resistances"),
            Input(value=self.data["immunities"], placeholder="Immunities", id="wiz-immunities"),
            Input(value=self.data["vulnerabilities"], placeholder="Vulnerabilities", id="wiz-vulnerabilities"),
            Static("[bold]Special Abilities[/]"),
            Horizontal(
                Input(placeholder="Name", id="wiz-special-name"),
                Input(placeholder="Description", id="wiz-special-desc"),
                id="wiz-special-inputs",
            ),
            Horizontal(
                Button("+ Add Special Ability", id="btn-wiz-add-special"),
                Button("Remove Selected", id="btn-wiz-remove-special"),
                id="wiz-special-actions",
            ),
            ListView(id="wiz-list-specials"),
        )
        self._refresh_wiz_attacks_list()
        self._refresh_wiz_specials_list()

    async def _build_step_review(self, container):
        if self.entity_type == "npc":
            lines = [
                f"[bold]{self.data['name'] or '(unnamed)'}[/] - NPC",
                f"  Race: {self.data['race']}   Role: {self.data['role']}",
                f"  Alignment: {self.data['alignment']}   Status: {self.data['status']}",
                f"  Location: {self.data['location']}",
            ]
            await container.mount(
                Static("[bold]Review & Create[/]"),
                Static("\n".join(lines), id="wiz-review-summary"),
            )
            return

        self._apply_class_defaults()
        abilities = self.data["abilities"]
        con_mod = shm.ability_modifier(abilities["con"])
        dex_mod = shm.ability_modifier(abilities["dex"])
        suggested_ac = shm.suggested_ac(dex_mod)
        if self.entity_type == "adventurer":
            suggested_hp = classes.suggested_hp(self.data["class_name"], self.data["level"], con_mod)
        else:
            suggested_hp = 10

        lines = [f"[bold]{self.data['name'] or '(unnamed)'}[/] - {ENTITY_LABELS[self.entity_type]}"]
        ability_parts = [
            f"{a.upper()} {abilities[a]} ({shm.format_modifier(shm.ability_modifier(abilities[a]))})"
            for a in shm.ABILITIES
        ]
        lines.append("  " + "  ".join(ability_parts))
        if self.entity_type == "adventurer":
            lines.append(f"  Class: {self.data['class_name']}   Level: {self.data['level']}")
        else:
            lines.append(f"  CR: {self.data['cr']}   Creature Type: {self.data['creature_type']}")
        if self.data["saving_throw_proficiencies"]:
            lines.append(f"  Saves: {', '.join(a.upper() for a in self.data['saving_throw_proficiencies'])}")
        if self.data["skill_proficiencies"]:
            lines.append(f"  Skills: {', '.join(shm.SKILL_LABELS[s] for s in self.data['skill_proficiencies'])}")
        if self.data["attacks"]:
            lines.append(f"  Attacks: {', '.join(a.get('name', '?') for a in self.data['attacks'])}")

        await container.mount(
            Static("[bold]Review & Create[/]"),
            Static("\n".join(lines), id="wiz-review-summary"),
            Label("Armor Class"),
            Input(value=str(self.data["ac"] if self.data["ac"] is not None else suggested_ac), id="wiz-final-ac"),
            Label("HP Max"),
            Input(value=str(self.data["hp_max"] if self.data["hp_max"] is not None else suggested_hp), id="wiz-final-hp"),
        )

    # -- step data collection ------------------------------------------

    def _collect_step_basic_npc(self):
        self.data["name"] = self.query_one("#wiz-name", Input).value.strip()
        self.data["race"] = self.query_one("#wiz-race", Input).value.strip()
        self.data["role"] = self.query_one("#wiz-role", Input).value.strip()
        align = self.query_one("#wiz-alignment", Select).value
        self.data["alignment"] = "" if align is Select.NULL else str(align)
        status = self.query_one("#wiz-status", Select).value
        self.data["status"] = "" if status is Select.NULL else str(status)
        self.data["location"] = self.query_one("#wiz-location", Input).value.strip()
        if not self.data["name"]:
            return "Name is required."
        return None

    def _collect_step_basic(self):
        self.data["name"] = self.query_one("#wiz-name", Input).value.strip()
        if self.entity_type == "adventurer":
            self.data["race"] = self.query_one("#wiz-race", Input).value.strip()
        align = self.query_one("#wiz-alignment", Select).value
        self.data["alignment"] = "" if align is Select.NULL else str(align)
        if not self.data["name"]:
            return "Name is required."
        return None

    def _collect_step_class_or_cr(self):
        if self.entity_type == "adventurer":
            self.data["class_name"] = str(self.query_one("#wiz-class", Select).value)
            try:
                self.data["level"] = max(1, int(self.query_one("#wiz-level", Input).value.strip() or 1))
            except ValueError:
                return "Level must be a number."
            self.data["saving_throw_proficiencies"] = list(classes.CLASS_SAVING_THROWS.get(self.data["class_name"], []))
        else:
            self.data["creature_type"] = self.query_one("#wiz-creature-type", Input).value.strip()
            self.data["cr"] = self.query_one("#wiz-cr", Input).value.strip() or "0"
        return None

    def _collect_step_abilities(self):
        scores = {}
        for a in shm.ABILITIES:
            raw = self.query_one(f"#wiz-ability-{a}", Input).value.strip()
            try:
                scores[a] = int(raw)
            except ValueError:
                return "Ability scores must be whole numbers."
        if not shm.matches_standard_array(scores):
            return f"Scores must use each Standard Array value exactly once: {shm.STANDARD_ARRAY}"
        self.data["abilities"] = scores
        return None

    def _collect_step_skills_saves(self):
        self.data["saving_throw_proficiencies"] = [a for a in shm.ABILITIES if self.query_one(f"#wiz-save-{a}", Switch).value]
        skills = {}
        for s in shm.SKILLS:
            value = str(self.query_one(f"#wiz-skill-{s}", Select).value)
            if value != "none":
                skills[s] = value
        self.data["skill_proficiencies"] = skills
        return None

    def _collect_step_attacks_traits(self):
        self.data["attacks"] = list(self.pending_attacks)
        self.data["special_abilities"] = list(self.pending_specials)
        self.data["resistances"] = self.query_one("#wiz-resistances", Input).value.strip()
        self.data["immunities"] = self.query_one("#wiz-immunities", Input).value.strip()
        self.data["vulnerabilities"] = self.query_one("#wiz-vulnerabilities", Input).value.strip()
        return None

    def _collect_step_review(self):
        if self.entity_type == "npc":
            return None
        try:
            self.data["ac"] = int(self.query_one("#wiz-final-ac", Input).value.strip())
            self.data["hp_max"] = int(self.query_one("#wiz-final-hp", Input).value.strip())
        except ValueError:
            return "AC and HP must be whole numbers."
        return None

    # -- helpers --------------------------------------------------------

    def _apply_class_defaults(self):
        """Make sure saving throws are seeded from the class even in quick
        mode, where the skills_saves step never runs to confirm them."""
        if self.entity_type == "adventurer" and not self.data["saving_throw_proficiencies"]:
            self.data["saving_throw_proficiencies"] = list(classes.CLASS_SAVING_THROWS.get(self.data["class_name"], []))

    def _reset_ability_inputs_to_standard_array(self):
        for a, score in zip(shm.ABILITIES, shm.STANDARD_ARRAY):
            self.query_one(f"#wiz-ability-{a}", Input).value = str(score)

    def _refresh_wiz_attacks_list(self):
        lv = self.query_one("#wiz-list-attacks", ListView)
        lv.clear()
        for atk in self.pending_attacks:
            bonus = shm.format_modifier(int(atk.get("bonus", 0) or 0))
            text = f"{atk.get('name', '?')} {bonus} to hit, {atk.get('damage', '')} {atk.get('damage_type', '')}".rstrip()
            lv.append(ListItem(Label(text)))

    def _refresh_wiz_specials_list(self):
        lv = self.query_one("#wiz-list-specials", ListView)
        lv.clear()
        for sa in self.pending_specials:
            lv.append(ListItem(Label(f"{sa.get('name', '?')}: {sa.get('description', '')}")))

    def _add_attack(self):
        name = self.query_one("#wiz-attack-name", Input).value.strip()
        if not name:
            return
        bonus_raw = self.query_one("#wiz-attack-bonus", Input).value.strip()
        try:
            bonus = int(bonus_raw) if bonus_raw else 0
        except ValueError:
            bonus = 0
        damage = self.query_one("#wiz-attack-damage", Input).value.strip()
        damage_type = self.query_one("#wiz-attack-damage-type", Input).value.strip()
        self.pending_attacks.append({"name": name, "bonus": bonus, "damage": damage, "damage_type": damage_type})
        for widget_id in ("#wiz-attack-name", "#wiz-attack-bonus", "#wiz-attack-damage", "#wiz-attack-damage-type"):
            self.query_one(widget_id, Input).value = ""
        self._refresh_wiz_attacks_list()

    def _remove_attack(self):
        lv = self.query_one("#wiz-list-attacks", ListView)
        if lv.index is not None and lv.index < len(self.pending_attacks):
            del self.pending_attacks[lv.index]
            self._refresh_wiz_attacks_list()

    def _add_special(self):
        name = self.query_one("#wiz-special-name", Input).value.strip()
        if not name:
            return
        desc = self.query_one("#wiz-special-desc", Input).value.strip()
        self.pending_specials.append({"name": name, "description": desc})
        self.query_one("#wiz-special-name", Input).value = ""
        self.query_one("#wiz-special-desc", Input).value = ""
        self._refresh_wiz_specials_list()

    def _remove_special(self):
        lv = self.query_one("#wiz-list-specials", ListView)
        if lv.index is not None and lv.index < len(self.pending_specials):
            del self.pending_specials[lv.index]
            self._refresh_wiz_specials_list()

    # -- final creation ---------------------------------------------------

    def _create_entity(self):
        from screens.entities import EntityDetailScreen
        from screens.sheet import CharacterSheetScreen

        if self.entity_type == "npc":
            fields = {
                "race": self.data["race"],
                "role": self.data["role"],
                "alignment": self.data["alignment"],
                "status": self.data["status"] or "Alive",
                "location": self.data["location"],
            }
            entity_id = db.create_entity("npc", self.data["name"], fields, "")
            self.dismiss(entity_id)
            self.app.push_screen(EntityDetailScreen(entity_id))
            return

        sheet_data = shm.default_sheet()
        sheet_data["abilities"] = dict(self.data["abilities"])
        sheet_data["ac"] = self.data["ac"]
        sheet_data["hp_max"] = self.data["hp_max"]
        sheet_data["hp_current"] = self.data["hp_max"]
        sheet_data["saving_throw_proficiencies"] = list(self.data["saving_throw_proficiencies"])
        sheet_data["skill_proficiencies"] = dict(self.data["skill_proficiencies"])
        sheet_data["attacks"] = list(self.data["attacks"])
        sheet_data["special_abilities"] = list(self.data["special_abilities"])
        sheet_data["resistances"] = self.data["resistances"]
        sheet_data["immunities"] = self.data["immunities"]
        sheet_data["vulnerabilities"] = self.data["vulnerabilities"]

        if self.entity_type == "adventurer":
            sheet_data["level"] = self.data["level"]
            flat_fields = {
                "race": self.data["race"],
                "class_name": self.data["class_name"],
                "level": str(self.data["level"]),
                "alignment": self.data["alignment"],
                "status": "Active",
            }
        else:
            sheet_data["cr"] = self.data["cr"]
            sheet_data["creature_type"] = self.data["creature_type"]
            flat_fields = {
                "creature_type": self.data["creature_type"],
                "cr": self.data["cr"],
                "alignment": self.data["alignment"],
                "status": "Alive",
            }
        flat_fields["sheet"] = sheet_data
        entity_id = db.create_entity(self.entity_type, self.data["name"], flat_fields, "")

        if self.link_to_npc_id:
            db.create_relationship(entity_id, self.link_to_npc_id, "hostile form of", "")

        self.dismiss(entity_id)
        if self.mode == "quick":
            self.app.push_screen(CharacterSheetScreen(entity_id))
        else:
            self.app.push_screen(EntityDetailScreen(entity_id))
