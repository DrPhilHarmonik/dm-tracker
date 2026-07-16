from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Label, Button, DataTable, Input, Select, TextArea, Static, ListView, ListItem, TabbedContent, TabPane, Switch
from textual.screen import Screen, ModalScreen
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
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

from screens.common import DismissableScreen, PALETTE, tint_border

SKILL_LEVEL_OPTIONS = [("None", "none"), ("Proficient", "proficient"), ("Expertise", "expertise")]


class CharacterSheetScreen(Screen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "save", "Save"),
        Binding("ctrl+e", "export_sheet", "Export Sheet"),
    ]

    def __init__(self, entity_id: int):
        super().__init__()
        self.entity_id = entity_id
        entity = db.get_entity(entity_id)
        self.entity_type = entity["type"]
        self.sheet = shm.normalize_sheet(entity["fields"].get("sheet", {}))
        self._inspiration = bool(entity["fields"].get("inspiration", False))
        self.pending_attacks: list[dict] = list(self.sheet["attacks"])
        self.pending_specials: list[dict] = list(self.sheet["special_abilities"])
        self.pending_spells: list[dict] = list(self.sheet["spells"])

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id="sheet-tabs"):
            with TabPane("Abilities", id="tab-abilities"):
                yield ScrollableContainer(Container(id="abilities-fields"), id="abilities-scroll")
            with TabPane("Combat", id="tab-combat"):
                yield ScrollableContainer(Container(id="combat-fields"), id="combat-scroll")
            with TabPane("Skills & Saves", id="tab-skills"):
                yield ScrollableContainer(Container(id="skills-fields"), id="skills-scroll")
            with TabPane("Attacks & Traits", id="tab-attacks"):
                yield ScrollableContainer(Container(id="attacks-fields"), id="attacks-scroll")
            with TabPane("Spells", id="tab-spells"):
                yield ScrollableContainer(Container(id="spells-fields"), id="spells-scroll")
        yield Horizontal(
            Button("Recalculate", id="btn-recalc", variant="primary"),
            Button("Save (Ctrl+S)", id="btn-save", variant="success"),
            Button("Export Sheet", id="btn-export-sheet", variant="default"),
            Button("Cancel", id="btn-cancel", variant="default"),
            id="sheet-actions",
        )
        yield Footer()

    async def on_mount(self):
        entity = db.get_entity(self.entity_id)
        self.title = f"{entity['name']} - Character Sheet"
        tint_border(self.query_one("#sheet-tabs"), self.entity_type)
        await self._build_abilities_tab()
        await self._build_combat_tab()
        await self._build_skills_tab()
        await self._build_attacks_tab()
        await self._build_spells_tab()
        self._refresh_computed_displays()

    # -- tab builders --------------------------------------------------

    async def _build_abilities_tab(self):
        container = self.query_one("#abilities-fields")
        abilities = shm.ABILITIES
        grid_rows = [
            Horizontal(
                *[
                    Vertical(
                        Label(a.upper(), classes="ability-cell-label"),
                        Input(value=str(self.sheet["abilities"][a]), id=f"sheet-ability-{a}", classes="ability-input"),
                        Static("+0", id=f"sheet-mod-{a}", classes="ability-mod"),
                        classes="ability-cell",
                    )
                    for a in abilities[i : i + 3]
                ],
                classes="ability-grid-row",
            )
            for i in range(0, 6, 3)
        ]
        await container.mount(*grid_rows)

    async def _build_combat_tab(self):
        container = self.query_one("#combat-fields")
        widgets = [
            Label("Armor Class"), Input(value=str(self.sheet["ac"]), id="sheet-ac", classes="stat-input"),
            Label("HP Max"), Input(value=str(self.sheet["hp_max"]), id="sheet-hp-max", classes="stat-input"),
            Label("HP Current"), Input(value=str(self.sheet["hp_current"]), id="sheet-hp-current", classes="stat-input"),
            Label("HP Temp"), Input(value=str(self.sheet["hp_temp"]), id="sheet-hp-temp", classes="stat-input"),
            Label("Hit Dice"), Input(value=self.sheet["hit_dice"], placeholder="e.g. 5d8+10", id="sheet-hit-dice"),
            Label("Speed (ft.)"), Input(value=str(self.sheet["speed"]), id="sheet-speed", classes="stat-input"),
        ]
        if self.entity_type == "enemy":
            widgets += [
                Label("Challenge Rating"), Input(value=self.sheet["cr"], placeholder="e.g. 1/2", id="sheet-cr", classes="stat-input"),
                Label("Creature Type"), Input(value=self.sheet["creature_type"], placeholder="e.g. Humanoid", id="sheet-creature-type"),
            ]
        else:
            widgets += [Label("Level"), Input(value=str(self.sheet["level"]), id="sheet-level", classes="stat-input")]
        widgets += [
            Label("Senses"), Input(value=self.sheet["senses"], placeholder="e.g. darkvision 60 ft.", id="sheet-senses"),
            Label("Languages"), Input(value=self.sheet["languages"], placeholder="e.g. Common, Elvish", id="sheet-languages"),
            Label("Proficiency Bonus (computed)"), Static("+2", id="sheet-prof-bonus"),
        ]
        if self.entity_type != "enemy":
            widgets += [
                Label("Inspiration"),
                Switch(value=self._inspiration, id="sheet-inspiration"),
            ]
        await container.mount(*widgets)

    async def _build_skills_tab(self):
        container = self.query_one("#skills-fields")
        save_rows = [
            Horizontal(
                Label(shm.ABILITY_LABELS[a], classes="save-label"),
                Switch(value=a in self.sheet["saving_throw_proficiencies"], id=f"sheet-save-{a}"),
                Static("+0", id=f"sheet-save-bonus-{a}", classes="save-bonus"),
                classes="save-row",
            )
            for a in shm.ABILITIES
        ]
        skill_rows = [
            Horizontal(
                Label(f"{shm.SKILL_LABELS[s]} ({shm.SKILLS[s].upper()})", classes="skill-label"),
                Select(SKILL_LEVEL_OPTIONS, value=self.sheet["skill_proficiencies"].get(s, "none"), id=f"sheet-skill-{s}", allow_blank=False),
                Static("+0", id=f"sheet-skill-bonus-{s}", classes="skill-bonus"),
                classes="skill-row",
            )
            for s in shm.SKILLS
        ]
        await container.mount(
            Static("[bold]Saving Throws[/]"), *save_rows,
            Static("[bold]Skills[/]"), *skill_rows,
        )

    async def _build_attacks_tab(self):
        container = self.query_one("#attacks-fields")
        await container.mount(
            Static("[bold]Attacks[/]"),
            Horizontal(
                Input(placeholder="Name", id="attack-name"),
                Input(placeholder="To-Hit Bonus", id="attack-bonus"),
                Input(placeholder="Damage (e.g. 1d6+2)", id="attack-damage"),
                Input(placeholder="Damage Type", id="attack-damage-type"),
                id="attack-inputs",
            ),
            Horizontal(
                Button("+ Add Attack", id="btn-add-attack"),
                Button("Remove Selected", id="btn-remove-attack"),
                id="attack-actions",
            ),
            ListView(id="list-attacks"),
            Static("[bold]Resistances / Immunities / Vulnerabilities[/]"),
            Input(value=self.sheet["resistances"], placeholder="Resistances", id="sheet-resistances"),
            Input(value=self.sheet["immunities"], placeholder="Immunities", id="sheet-immunities"),
            Input(value=self.sheet["vulnerabilities"], placeholder="Vulnerabilities", id="sheet-vulnerabilities"),
            Static("[bold]Special Abilities[/]"),
            Horizontal(
                Input(placeholder="Name", id="special-name"),
                Input(placeholder="Description", id="special-desc"),
                id="special-inputs",
            ),
            Horizontal(
                Button("+ Add Special Ability", id="btn-add-special"),
                Button("Remove Selected", id="btn-remove-special"),
                id="special-actions",
            ),
            ListView(id="list-specials"),
        )
        self._refresh_attacks_list()
        self._refresh_specials_list()

    async def _build_spells_tab(self):
        container = self.query_one("#spells-fields")
        pb = shm.proficiency_bonus(self.entity_type, self.sheet)
        spell_ability = self.sheet.get("spellcasting_ability") or ""

        header_widgets = []
        if spell_ability:
            dc = 8 + pb + shm.ability_modifier(self.sheet["abilities"].get(spell_ability, 10))
            atk = pb + shm.ability_modifier(self.sheet["abilities"].get(spell_ability, 10))
            label = shm.ABILITY_LABELS.get(spell_ability, spell_ability.upper())
            header_widgets.append(Static(
                f"[bold]Spellcasting[/]  Ability: {label}  |  Spell Save DC: {dc}  |  Spell Attack: {shm.format_modifier(atk)}",
                id="spell-stats",
            ))

        slot_rows = [Static("[bold]Spell Slots  (current / max)[/]")]
        for lvl in range(1, 10):
            slot = self.sheet["spell_slots"][str(lvl)]
            slot_rows.append(
                Horizontal(
                    Label(f"Lv {lvl}", classes="slot-label"),
                    Input(value=str(slot["current"]), id=f"slot-current-{lvl}", classes="slot-input"),
                    Label("/", classes="slot-sep"),
                    Input(value=str(slot["max"]), id=f"slot-max-{lvl}", classes="slot-input"),
                    classes="slot-row",
                )
            )

        spell_form = [
            Static("[bold]Spells[/]"),
            Horizontal(
                Input(placeholder="Spell name", id="spell-name"),
                Select(
                    [("Cantrip", "0")] + [(f"Level {i}", str(i)) for i in range(1, 10)],
                    value="0",
                    id="spell-level",
                    allow_blank=False,
                ),
                Select(
                    [("Action", "action"), ("Bonus Action", "bonus_action"),
                     ("Reaction", "reaction"), ("Free", "free")],
                    value="action",
                    id="spell-action-cost",
                    allow_blank=False,
                ),
                id="spell-form-row1",
            ),
            Horizontal(
                Select(
                    [("None", "none"), ("Save", "save"), ("Attack", "attack")],
                    value="none",
                    id="spell-save-or-attack",
                    allow_blank=False,
                ),
                Select(
                    [("--", "")] + [(shm.ABILITY_LABELS[a], a) for a in shm.ABILITIES],
                    value="",
                    id="spell-save-ability",
                    allow_blank=True,
                ),
                Input(placeholder="Description (optional)", id="spell-description"),
                id="spell-form-row2",
            ),
            Horizontal(
                Button("+ Add Spell", id="btn-add-spell"),
                Button("Remove Selected", id="btn-remove-spell"),
                id="spell-actions",
            ),
            ListView(id="list-spells"),
        ]
        await container.mount(*header_widgets, *slot_rows, *spell_form)
        self._refresh_spells_list()

    # -- pending attack/special list management ------------------------

    def _refresh_attacks_list(self):
        lv = self.query_one("#list-attacks", ListView)
        lv.clear()
        for atk in self.pending_attacks:
            bonus = shm.format_modifier(int(atk.get("bonus", 0) or 0))
            text = f"{atk.get('name', '?')} {bonus} to hit, {atk.get('damage', '')} {atk.get('damage_type', '')}".rstrip()
            lv.append(ListItem(Label(text)))

    def _refresh_specials_list(self):
        lv = self.query_one("#list-specials", ListView)
        lv.clear()
        for sa in self.pending_specials:
            lv.append(ListItem(Label(f"{sa.get('name', '?')}: {sa.get('description', '')}")))

    def _add_attack(self):
        name = self.query_one("#attack-name", Input).value.strip()
        if not name:
            return
        bonus_raw = self.query_one("#attack-bonus", Input).value.strip()
        try:
            bonus = int(bonus_raw) if bonus_raw else 0
        except ValueError:
            bonus = 0
        damage = self.query_one("#attack-damage", Input).value.strip()
        damage_type = self.query_one("#attack-damage-type", Input).value.strip()
        self.pending_attacks.append({"name": name, "bonus": bonus, "damage": damage, "damage_type": damage_type})
        for widget_id in ("#attack-name", "#attack-bonus", "#attack-damage", "#attack-damage-type"):
            self.query_one(widget_id, Input).value = ""
        self._refresh_attacks_list()

    def _remove_attack(self):
        lv = self.query_one("#list-attacks", ListView)
        if lv.index is not None and lv.index < len(self.pending_attacks):
            del self.pending_attacks[lv.index]
            self._refresh_attacks_list()

    def _add_special(self):
        name = self.query_one("#special-name", Input).value.strip()
        if not name:
            return
        desc = self.query_one("#special-desc", Input).value.strip()
        self.pending_specials.append({"name": name, "description": desc})
        self.query_one("#special-name", Input).value = ""
        self.query_one("#special-desc", Input).value = ""
        self._refresh_specials_list()

    def _remove_special(self):
        lv = self.query_one("#list-specials", ListView)
        if lv.index is not None and lv.index < len(self.pending_specials):
            del self.pending_specials[lv.index]
            self._refresh_specials_list()

    def _refresh_spells_list(self):
        lv = self.query_one("#list-spells", ListView)
        lv.clear()
        for sp in self.pending_spells:
            lvl_label = "Cantrip" if sp["level"] == 0 else f"L{sp['level']}"
            cost = sp.get("action_cost", "action").replace("_", " ")
            sor = sp.get("save_or_attack", "none")
            sor_label = f" [bold cyan]({sor})[/bold cyan]" if sor != "none" else ""
            lv.append(ListItem(Label(f"{sp['name']} ({lvl_label}, {cost}{sor_label})")))

    def _add_spell(self):
        name = self.query_one("#spell-name", Input).value.strip()
        if not name:
            return
        level = int(str(self.query_one("#spell-level", Select).value))
        action_cost = str(self.query_one("#spell-action-cost", Select).value)
        save_or_attack = str(self.query_one("#spell-save-or-attack", Select).value)
        raw_save_ability = self.query_one("#spell-save-ability", Select).value
        save_ability = "" if raw_save_ability is Select.BLANK else str(raw_save_ability)
        description = self.query_one("#spell-description", Input).value.strip()
        self.pending_spells.append({
            "name": name,
            "level": level,
            "action_cost": action_cost,
            "save_or_attack": save_or_attack,
            "save_ability": save_ability,
            "description": description,
        })
        self.query_one("#spell-name", Input).value = ""
        self.query_one("#spell-description", Input).value = ""
        self._refresh_spells_list()

    def _remove_spell(self):
        lv = self.query_one("#list-spells", ListView)
        if lv.index is not None and lv.index < len(self.pending_spells):
            del self.pending_spells[lv.index]
            self._refresh_spells_list()

    # -- collecting + computed display ----------------------------------

    def _to_int(self, widget_id: str, default: int = 0) -> int:
        raw = self.query_one(f"#{widget_id}", Input).value.strip()
        try:
            return int(raw) if raw else default
        except ValueError:
            return default

    def _to_text(self, widget_id: str) -> str:
        return self.query_one(f"#{widget_id}", Input).value.strip()

    def _collect_sheet_from_widgets(self) -> dict:
        abilities = {a: self._to_int(f"sheet-ability-{a}", 10) for a in shm.ABILITIES}
        saving_throw_proficiencies = [a for a in shm.ABILITIES if self.query_one(f"#sheet-save-{a}", Switch).value]

        skill_proficiencies = {}
        for s in shm.SKILLS:
            value = str(self.query_one(f"#sheet-skill-{s}", Select).value)
            if value != "none":
                skill_proficiencies[s] = value

        spell_slots = {}
        for lvl in range(1, 10):
            try:
                cur_raw = self.query_one(f"#slot-current-{lvl}", Input).value.strip()
                max_raw = self.query_one(f"#slot-max-{lvl}", Input).value.strip()
                cur = max(0, int(cur_raw)) if cur_raw else 0
                mx = max(0, int(max_raw)) if max_raw else 0
            except Exception:
                cur, mx = 0, 0
            spell_slots[str(lvl)] = {"current": cur, "max": mx}

        # Start from the existing sheet so fields not editable here
        # (spellcasting_ability, proficiencies, etc.) are preserved.
        sheet = dict(self.sheet)
        sheet.update({
            "abilities": abilities,
            "ac": self._to_int("sheet-ac", 10),
            "hp_max": self._to_int("sheet-hp-max", 10),
            "hp_current": self._to_int("sheet-hp-current", 10),
            "hp_temp": self._to_int("sheet-hp-temp", 0),
            "hit_dice": self._to_text("sheet-hit-dice"),
            "speed": self._to_int("sheet-speed", 30),
            "saving_throw_proficiencies": saving_throw_proficiencies,
            "skill_proficiencies": skill_proficiencies,
            "senses": self._to_text("sheet-senses"),
            "languages": self._to_text("sheet-languages"),
            "resistances": self._to_text("sheet-resistances"),
            "immunities": self._to_text("sheet-immunities"),
            "vulnerabilities": self._to_text("sheet-vulnerabilities"),
            "attacks": list(self.pending_attacks),
            "special_abilities": list(self.pending_specials),
            "spells": list(self.pending_spells),
            "spell_slots": spell_slots,
        })
        if self.entity_type == "enemy":
            sheet["cr"] = self._to_text("sheet-cr")
            sheet["creature_type"] = self._to_text("sheet-creature-type")
        else:
            sheet["level"] = self._to_int("sheet-level", 1)
        return sheet

    def _refresh_computed_displays(self):
        sheet = self._collect_sheet_from_widgets()
        pb = shm.proficiency_bonus(self.entity_type, sheet)

        for a in shm.ABILITIES:
            mod = shm.ability_modifier(sheet["abilities"][a])
            self.query_one(f"#sheet-mod-{a}", Static).update(shm.format_modifier(mod))
            self.query_one(f"#sheet-save-bonus-{a}", Static).update(
                shm.format_modifier(shm.saving_throw_bonus(sheet, a, pb))
            )
        for s in shm.SKILLS:
            self.query_one(f"#sheet-skill-bonus-{s}", Static).update(
                shm.format_modifier(shm.skill_bonus(sheet, s, pb))
            )
        self.query_one("#sheet-prof-bonus", Static).update(shm.format_modifier(pb))
        self.sheet = sheet
        # Update spellcasting stat bar if the tab has been built
        try:
            spell_ability = sheet.get("spellcasting_ability") or ""
            if spell_ability:
                dc = shm.spell_save_dc(sheet, self.entity_type)
                atk = shm.spell_attack_bonus(sheet, self.entity_type)
                label = shm.ABILITY_LABELS.get(spell_ability, spell_ability.upper())
                self.query_one("#spell-stats", Static).update(
                    f"[bold]Spellcasting[/]  Ability: {label}  |  Spell Save DC: {dc}  |  Spell Attack: {shm.format_modifier(atk)}"
                )
        except Exception:
            pass

    # -- actions ----------------------------------------------------------

    def action_save(self):
        sheet = self._collect_sheet_from_widgets()
        entity = db.get_entity(self.entity_id)
        fields = dict(entity["fields"])
        fields["sheet"] = sheet
        # The sheet is the authoritative source for these -- keep the flat
        # copies (used by list columns and the detail view) from drifting.
        if self.entity_type == "enemy":
            fields["cr"] = sheet["cr"]
            fields["creature_type"] = sheet["creature_type"]
        else:
            fields["level"] = str(sheet["level"])
            try:
                fields["inspiration"] = self.query_one("#sheet-inspiration", Switch).value
            except Exception:
                pass
        db.update_entity(self.entity_id, entity["name"], fields, entity["notes"])
        self.dismiss(True)

    def action_cancel(self):
        self.dismiss(False)

    def action_export_sheet(self):
        try:
            path = exp.export_entity_sheet(self.entity_id)
            self.app.notify(f"Exported to {path}", severity="information")
        except Exception as exc:
            self.app.notify(f"Export failed: {exc}", severity="error")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-save":
            self.action_save()
        elif event.button.id == "btn-export-sheet":
            self.action_export_sheet()
        elif event.button.id == "btn-cancel":
            self.action_cancel()
        elif event.button.id == "btn-recalc":
            self._refresh_computed_displays()
        elif event.button.id == "btn-add-attack":
            self._add_attack()
        elif event.button.id == "btn-remove-attack":
            self._remove_attack()
        elif event.button.id == "btn-add-special":
            self._add_special()
        elif event.button.id == "btn-remove-special":
            self._remove_special()
        elif event.button.id == "btn-add-spell":
            self._add_spell()
        elif event.button.id == "btn-remove-spell":
            self._remove_spell()
