# DM Tracker — Build History & Roadmap

30 phases complete, Phases 31-34 planned. The core feature set covers the full D&D 5e session loop:
character creation (wizard, D&D Beyond import, CSV, Foundry VTT, Roll20),
character sheets (abilities, combat, skills & saves, attacks, spells), combat
tracking (initiative, turn order, HP, conditions, death saves, action economy,
spellcasting, summons, combat log), active effects, encounter balance, session
notes, multi-campaign support, in-session quick capture, party rest, party
overview, XP tracking, SRD monster reference (322 monsters) with Add-to-Campaign,
allied NPC combat forms, encounter generator, quest objectives, relationship
browser, session timeline, and character sheet export.

---

## Confirmed design decisions

- **Ruleset:** D&D 5e (SRD) -- six ability scores, proficiency bonus, skills,
  saving throws, AC, HP, standard classes/races.
- **Entity model:** NPCs keep their lightweight, social-focused schema (race, role,
  alignment, status, location). **Enemy** holds the full combat stat block (CR, AC,
  HP, abilities, attacks, resistances, etc.). Adventurers get the full stat block
  too, since they're played in combat.
- **Hostile NPCs (BG3-style):** an NPC never mutates into an Enemy in place.
  "Make Hostile" creates a linked Enemy record and connects it back via a
  `hostile form of` relationship. The original NPC is never touched.
- **Ability score generation (wizard):** Standard Array (15/14/13/12/10/8),
  assigned by the DM during character creation.
- **Time/tick system:** round-based only, scoped to an active encounter. Effect
  durations are counted in rounds; nothing decays automatically outside of combat.
- **Effects stack additively.** Multiple effects on the same stat are summed; no
  attempt to replicate 5e's same-named-bonus rules.
- **Mechanical enforcement is reference-only.** Conditions, resistances, and
  special abilities surface as reminders; the DM applies the mechanical consequences.
  The app doesn't intercept rolls to add advantage for Prone, etc.

---

## TUI Review Passes

Screenshot-based visual review supplements the automated UI tests, since those
tests drive screens programmatically but do not inspect rendered layouts.

**Pass 1 -- 2026-06-21.** Caught and fixed: edit-flat-fields silently wiped
`sheet`/`active_effects`/`combat` data (critical data-loss bug); Start Encounter
resettable mid-combat; flat/nested level-CR desync; unstyled ListView; oversized
number inputs.

**Pass 2 -- 2026-07-15.** Caught and fixed: dashboard button row clipped
"Backup/Restore" to "Bac" at 160 cols (root cause: 8 buttons * `min-width:20`
= 160, no room for gaps; reduced to 16); "1 entries" grammar on entity cards;
`AwardXPScreen` crash when XP stored as a string (`:,` format spec requires int);
"I" inspiration column header renamed "Insp"; abilities tab was 6 stacked rows
wasting 75% of horizontal space -- replaced with a 3×2 grid; skill proficiency
Selects were full-width -- constrained to width 24; entity-type bindings hidden
from footer (already shown as cards) so the newer `r`/`p`/`^x`/`m`/`^w`/`^n`
bindings now appear.

---

## Phases

### Phase 1 -- Character Sheet Data Model

**Status: Done.** New `sheet.py` module: 5e math (ability modifiers, proficiency
bonus by level/CR, saving throw and skill bonuses), `normalize_sheet()`. New
`enemy` entity type alongside `adventurer`, both backed by `fields["sheet"]` JSON.
Dedicated tabbed `CharacterSheetScreen` (Abilities / Combat / Skills & Saves /
Attacks & Traits) reachable from any adventurer/enemy's detail view. `hostile form
of` relationship type added. 16/16 tests.

### Phase 2 -- Dice Rolling Engine

**Status: Done.** New `dice.py`: generic notation parser/roller (`2d6+3`,
`4d6kh3`/`kl3`), 5e-aware wrappers (`roll_d20` with advantage/disadvantage,
`roll_ability_check`, `roll_saving_throw`, `roll_skill_check`, `roll_attack`,
`roll_damage`). `RollPickerScreen` (Ability/Save, Skills, Attacks, Custom tabs)
with advantage toggles and in-session roll history (not persisted). 29/29 tests.

### Phase 3 -- Encounter / Combat Tracker

**Status: Done.** New `combat.py`: combatant list, initiative order, round/turn
pointer, condition ticking and expiry, HP reads/writes straight from entity sheets
(no HP duplication). New `encounter` entity type; dashboard becomes 3x3 grid.
`CombatTrackerScreen` (Combatants / HP & Conditions / Turn Controls tabs).
"Make Hostile" on NPC detail clones to linked Enemy via `hostile form of`.

Real bug fixed: `Select.set_options()` always resets selection (documented
behavior); refreshing combatant dropdowns after every action was silently wiping
the DM's selection. Fixed by capturing and restoring the selected value around
every `set_options()` call. 44/44 tests.

### Phase 4 -- Active Effects & Time-Tick System

**Status: Done.** Active effects live in `fields["active_effects"]` list, never
baked into the base sheet. `apply_to_sheet()` computes effective stats on read.
Effects modify the six abilities, AC, or speed; multiple effects on the same stat
stack additively. Effects only decay on combat round-advance (`tick_effects()`
wired into Next Turn/Next Round). Expired effects surface as a notice. "Effects"
screen (`f` key) on any adventurer/enemy detail.

Real bug fixed: `app.pop_screen()` silently discards any callback registered via
`push_screen(..., callback=...)` without invoking it -- only `Screen.dismiss()`
fires it. Every screen using `Binding("escape", "app.pop_screen", ...)` whose
caller expected a refresh was silently never refreshing. Fixed via shared
`DismissableScreen` base class throughout. 52/52 tests.

### Phase 5 -- NPC/Adventurer/Enemy Creation Wizard

**Status: Done.** New `classes.py` reference (12 core 5e classes, hit dice,
suggested saves). `WizardScreen` supports all three entity types in Quick and
Advanced modes. "Make Hostile" routes through Enemy/Quick mode prefilled from
the source NPC; cancelling leaves no orphaned entity. 61/61 tests.

### Phase 6 -- Polish & Export Integration

**Status: Done.** CSS cleanup: standardized action-row/button patterns,
consolidated status-message rules across sheet, roll, combat, wizard, export,
and backup screens. New `screens/common.format_io_error()` categorizes
export/import/backup failures (JSON parse, YAML parse, permission, missing path,
is-a-directory, generic validation, filesystem). Full regression pass: 76/76
tests, plus headless smoke run through every core flow in one continuous session.

### Phase 7 -- Maintainability Refactor

**Status: Done.** `app.py` reduced to the app root + imports. Screen code split
into `screens/` by feature area: `dashboard`, `entities`, `sheet`, `roll`,
`combat`, `effects`, `wizard`, `backup`, `modals`, `common`. Mechanical split
only; no behavioral cleanup. Local imports used where needed to avoid circular
imports. 76/76 tests.

### Phase 8 -- UI Interaction Tests

**Status: Done.** Five pilot test files drive the real `DMApp` through a headless
Pilot session (plain `asyncio.run()`, no `pytest-asyncio` dependency):
`test_ui_dismissal.py`, `test_ui_wizard.py`, `test_ui_backup.py`,
`test_ui_e2e.py` (wizard create → sheet edit → roll → effect → combat round →
vault export in one session). 93/93 tests.

### Phase 9 -- Data Integrity Layer

**Status: Done.** `db.py` is the single write chokepoint. `validate_entity_type()`,
`validate_relationship_type()`, `validate_fields()` (strict, for live single-entity
writes), `normalize_special_fields()` (lenient, for bulk import). `replace_all`
validates everything before deleting anything. `update_entity` raises on missing ID.
`create_relationship` checks both endpoints. 20 new tests, 113 total.

### Phase 10 -- Session Workflow

**Status: Done.** New `session_workflow.py`: `player_characters()`,
`active_quests()`, `active_encounters()`, `notable_npcs()`, `recent_notes()` --
all computed from existing data on read, no new schema. `SessionWorkflowScreen`
reachable from any Session's detail view; five DataTable sections with buttons
navigating into existing screens (Sheet, Combat Tracker, Detail). 129/129 tests.

### Phase 11 -- Spellcasting, Action Economy, Summons

**Status: Done.** Sheet gained `spells` list + `spell_slots` (levels 1-9) +
`spellcasting_ability`. `attacks` entries gained `action_cost`. Combat tracker
tracks Action/Bonus Action/Reaction per turn; weapon/spell options prefixed
`[W]`/`[S]`; spell saves show DC; spell attacks roll proficiency+ability; slots
decrement on cast. Fifth "Spells" tab on character sheet. Summons (Phase 11b):
"Summon Creature" in Turn Controls opens Quick Wizard to create an Enemy entity;
on completion a `summoned by` relationship is auto-created and the creature is
added to the encounter. 251/251 tests.

### Phase 12 -- Defined Races with Integrated Stat Bonuses

**Status: Done.** New `races.py` (13 SRD-legal race/subrace entries). Wizard
gained a Race step (adventurer-only, between Basic Info and Class & Level).
Half-Elf has a "choose 2 abilities for +1 each" sub-step, validated against
picking the same ability twice. Bonuses bake into a derived copy at creation
only; the raw Standard Array is never mutated so navigating Back re-validates
correctly. 144/144 tests.

Real bug fixed: the race Select fires a `Changed` event on its own initial mount
(no-value → default), re-entrantly re-rendering the step while the original mount
was still in progress, corrupting a later step's Select (~40% of e2e runs failed).
Fixed by only re-rendering when the new value actually differs.

### Phase 13 -- Defined Classes (Class-Driven Logic)

**Status: Done** (landed alongside Phase 12). `classes.py` gained
`CLASS_SPELLCASTING_ABILITY`, `CLASS_PRIMARY_ABILITY`, `CLASS_PROFICIENCIES`,
and `suggested_hp()`. Wizard abilities step shows primary/spellcasting hint;
saves are suggested from `CLASS_SAVING_THROWS`; proficiencies bake into
`sheet["proficiencies"]` on create.

### Phase 14 -- Conditions & Death Saves

**Status: Done.** New `conditions.py`: 15 SRD conditions with 1-2 sentence
mechanical summaries. Combat tracker's freeform condition Input replaced by a
Select picker; selecting a condition shows its description in blue below.
"Custom..." option reveals a text Input for homebrew conditions. Death saves
appear automatically when an Adventurer combatant is at 0 HP: + Success /
+ Failure buttons; 3 successes → Stable; 3 failures → Dead. `combat.py` gained
`add_death_save()` and `reset_death_saves()`. 19 new tests.

### Phase 15 -- Encounter Balance Calculator

**Status: Done.** New `encounter_balance.py`: full SRD CR-to-XP table (CR 0-30),
DMG per-character level thresholds (Easy/Medium/Hard/Deadly for levels 1-20),
DMG encounter multipliers by enemy count. Live `#balance-readout` widget in the
Combatants tab: difficulty label in matching color, adjusted XP with multiplier,
next threshold. 15 new tests.

### Phase 16 -- Character Import (D&D Beyond & CSV)

**Status: Done.** New `importers/` package: `ddb.py` (D&D Beyond character export
JSON → entity dict, with and without the `"data"` wrapper), `csv_import.py`
(unified-header CSV, all entity types, Download Template option). Shared
`import_entity()` (always additive, warns on duplicate names). Both wired into
Backup & Restore. Fixture files in `tests/fixtures/`. 23 new tests, 216 total.

### Phase 17 -- Multi-Campaign Support

**Status: Done.** New `campaign_manager.py`: registry DB at
`~/.local/share/dm_tracker/campaigns.db`; campaign files at
`~/.local/share/dm_tracker/campaigns/<name>.db`. `db.set_db_path()` switches
the active DB at runtime. Auto-creates "My Campaign" on first run.
`CampaignSwitcherScreen` (DataTable with name, last opened, entity count, path;
Open/Rename/Delete + Create Campaign). Dashboard title shows campaign name.
`DM_DB_PATH` still bypasses the manager. 18 new tests, 234 total.

### Phase 18 -- In-Session Quick Capture

**Status: Done.** `screens/quick_capture.py` -- `QuickCaptureModal` opens from
`^n` anywhere in the app. Single-field overlay: Enter saves, Tab reveals an
entity tag field (live-filtered autocomplete, up to 10 matches). Note appends to
the active session's notes field; tagged entity also receives it. No session?
Warns and requires an entity tag. `[Round N]` prefix auto-injected when a
`CombatTrackerScreen` is in the screen stack. `db.latest_session()` picks the
most recently created session; cached on the App for the run. 14 new tests,
248 total.

### Phase 19 -- Rest Mechanics

**Status: Done.** New `rest.py`: `long_rest()` restores all HP and all spell slots
for every active adventurer; `short_rest()` spends hit dice for one adventurer
(validates against remaining dice, returns HP gained and dice spent).
`RestScreen` reachable from `r` on the dashboard (Party Rest button). Long Rest
section: single "Apply Long Rest to All" button. Short Rest section: one card per
active adventurer showing current HP, AC, hit die per-roll, remaining spell slots;
a number-of-dice Input and "Roll & Apply" button per card. 12 new tests, 260 total.

### Phase 20 -- Party Overview Panel

**Status: Done.** `screens/party_overview.py` -- `PartyOverviewScreen` is a
read-only DataTable of all active adventurers. Columns: Name, Insp (★ in yellow or
dim --), Class, HP (color-coded: green >50%, yellow 25-50%, red ≤25%, bold red at
0), AC, XP (shows "LEVEL UP!" in bold green when XP exceeds current level
threshold), Conditions (pulled from any started encounter), Spell Slots (formatted
"L1:3/4  L2:1/3" for non-zero-max levels), Active Effects. Refreshes on
re-enter. `p` key on dashboard. 12 new tests, 272 total.

### Phase 21 -- XP Tracking & Inspiration

**Status: Done.** New `xp.py`: full 5e XP threshold table (levels 1-20),
`level_from_xp()`, `xp_for_next_level()`, `should_level_up()`, `split_xp()`.
`AwardXPScreen`: enter total XP earned for the encounter, live per-PC split label
(cyan), roster showing each adventurer's current XP/threshold and level, "Award
XP" button persists and notifies of any level-ups. Adventurer schema gained `xp`
(number) and `inspiration` (boolean) fields. `CharacterSheetScreen` Combat tab
gained an inspiration Switch for non-enemy entities; `action_save()` persists it.
`^x` key on dashboard. 21 new tests, 293 total.

### Phase 22 -- SRD Monster Reference & Character Sheet Export

**Status: Done.** Two features:

**SRD Monster Reference:** New `srd.py` (33 hand-curated SRD monsters, CR 0
Commoner through CR 21 Lich). `search(query)` matches name or CR;
`find(name)` exact match; `wizard_prefill(monster)` returns a dict compatible
with `WizardScreen.data`. `screens/monster_ref.py` -- two-panel layout (search
Input + ListView left, stat block detail Static right). Highlighting a list item
shows the full stat block; "Add to Campaign" opens the enemy Quick Wizard
prefilled from the selected monster. `m` key on dashboard.

**Character Sheet Export:** `export.export_entity_sheet(entity_id, path=None)`
wraps the existing `_render_entity()` into a standalone file write (YAML
frontmatter + sheet stats + relationships + notes). Default path:
`~/dm_exports/<slugified-name>_sheet.md`. "Export Sheet" button and `^e` binding
on `CharacterSheetScreen`; toast shows saved path. 26 new tests, 322 total.

### Phase 23 -- Full SRD Monster Expansion

**Status: Done.** `data/monsters.json` -- 322 SRD monsters fetched from open5e,
converted to the app's schema via `dev/build_srd.py`. `srd.py` loads from the
JSON at import time; the original 33-entry list is kept as a fallback.
Attacks correctly separated from save-based specials (breath weapons, multiattack)
by checking for "to hit" in the action description. `MonsterRefScreen` and
`wizard_prefill()` needed no changes. Note: Beholder, Mind Flayer, and Banshee
are not in the WotC SRD CC -- they are product identity and absent from the
open5e `wotc-srd` dataset. 9 new tests, 331 total.

### Phase 23a -- Make Allied (NPC Allied Combat Forms)

**Status: Done.** Mirror of "Make Hostile": "Make Allied" button (`y`) on any
NPC detail screen opens the Enemy Quick Wizard prefilled with `(Allied)` in the
name. On completion, writes an `allied form of` relationship back to the NPC.
`allied form of` added to `RELATIONSHIP_TYPES`. `WizardScreen` gained a
`link_rel_type` parameter (defaults to `"hostile form of"` for backward compat).
3 new tests, 325 total.

### Phase 24 -- Combat Log

**Status: Done.** `combat.py` gained `log_entry()` and a `"log"` key in the
combat state (persisted in `fields["combat"]`). `CombatTrackerScreen` gained a
"Log" tab showing entries newest-first with `[RN]` round prefixes. Logged events:
encounter start/end, HP damage/heal (with before → after values), conditions
added/removed, death save results with resolution, and turn/round advances.
7 new tests, 339 total.

### Phase 25 -- Encounter Generator

**Status: Done.** New `encounter_gen.py`: `generate(party_levels, difficulty,
pool, seed)` tries monster counts 1-6, computes the raw XP budget for each
(target adjusted XP / multiplier), samples candidates close to the per-monster
budget, and returns whichever configuration lands closest to the target. New
`EncounterGenScreen`: party size + average level + difficulty inputs; DataTable
of results (Name, CR, Type, HP, AC, XP); Regenerate reshuffles; "Add All to
Campaign" creates Enemy entities from the selection. `g` key on dashboard.
9 new tests, 347 total.

### Phase 26 -- Quest Objectives

**Status: Done.** Quest `fields["objectives"]` is now a validated list of
`{text, done}` dicts. `normalize_special_fields()` handles migration for existing
quest records (missing key defaults to `[]`). Quest detail screen gained an
Objectives table, an Add Objective modal, and a toggle action/button for the
selected objective. Objective completion progress is surfaced in `EntityListScreen`
and `SessionWorkflowScreen` (e.g. "3 / 5 complete"). 7 new tests, 354 total.

### Phase 27 -- Relationship Browser

**Status: Done.** New `screens/relationships.py` --
`RelationshipBrowserScreen`. Loads every entity and every relationship from the
DB; renders a dense table grouped by entity type with direction, relationship
type, and related entity columns. Filter bar narrows to a single entity type.
Selecting a relationship row pushes `EntityDetailScreen` for the related entity;
entities without relationships open themselves. `R` key on dashboard; also
reachable from any entity detail view. No external graph library required --
pure Textual widgets. 4 new tests, 358 total.

### Phase 28 -- Calendar & Session Timeline

**Status: Done.** New `cal.py`: named calendar presets (Gregorian and Forgotten
Realms Calendar of Harptos -- 12 months of 30 days each plus 5 intercalary days:
Midwinter, Greengrass, Midsummer, Highharvestide, Feast of the Moon).
`sort_sessions()` orders session entities by `session_number` ascending; sessions
without one sort last. New `TimelineScreen` (`t` key on dashboard): DataTable of
all sessions showing #, In-Game Date, Real Date, Name, and notes preview (first
60 chars). Sessions without a number sort to the bottom. Selecting a row opens
the session's `EntityDetailScreen`. `in_game_date` remains a freeform text field
-- the DM writes whatever format suits their campaign. 15 new tests, 373 total.

### Phase 29 -- VTT Importers

**Status: Done.** Three new importers in `importers/`:

- `foundry.py` -- Foundry VTT actor JSON (exported via Actors sidebar >
  right-click > Export Data). Actor type `"character"` → adventurer; `"npc"` →
  enemy with CR parsed from `system.details.cr` (fractional CRs mapped to
  `"1/8"`, `"1/4"`, `"1/2"`). Skill proficiencies read from Foundry skill
  abbreviations (`"ath"`, `"prc"`, etc.). Biography HTML stripped.
- `roll20.py` -- Roll20 "D&D 5e by Roll20" sheet JSON (community API export,
  schema_version 3). Accepts bare character object or `{"characters": [...]}` 
  wrapper. Attributes read from flat `attribs` list; skill proficiencies from
  `<skill>_prof` convention (1 = proficient, 2 = expertise).
- `ddb_encounter.py` -- D&D Beyond encounter JSON → one encounter entity plus
  one enemy per monster type, linked via `involves` relationships. Monster stat
  blocks resolved against the local SRD; unknowns created with minimal stats and
  a note flagging manual completion. Accepts `"quantity"`, `"count"`, or
  `"number"` for per-monster count; `"monsters"` or `"creatures"` for the list
  key. Also fixed a latent bug in `encounter_gen.py` where `ac`/`hp_max`/
  resistances were passed as flat entity fields instead of inside the sheet.

All three wired into Backup & Restore. 32 new tests, 405 total.

### Phase 30 -- Party Loot Tracker

**Status: Done.** `fields["loot"]` added as a special field on session
entities: a list of `{name, qty, value, owner}` dicts. `normalize_loot()`
validates and normalizes entries; `normalize_special_fields()` handles
migration (missing key defaults to `[]`). New `db` helpers:
`add_loot_entry()`, `assign_loot()`, `remove_loot_entry()`,
`unassigned_loot()`. New `LootScreen` reachable from session entity detail
(`l` keybinding, "Loot" button): DataTable of loot entries with Add / Assign
/ Unassign / Remove actions; "Assign" opens a picker over active adventurers
and sets `owner`. `PartyOverviewScreen` gains an Unassigned Loot section
listing items with no owner across all sessions. 21 new tests, 426 total.

### Phase 31 -- Level-Up Workflow

**Status: Planned.**

`LevelUpScreen` triggered automatically when an adventurer's XP crosses a
threshold (from `AwardXPScreen` or `PartyOverviewScreen`), or manually from
`CharacterSheetScreen` via a "Level Up" button. Steps: confirm new level,
roll (or enter) new HP (hit die + CON mod, with "take average" option),
update spell slot maximums from `classes.py` tables, display a class-feature
checklist at the new level (text reference only -- DM applies them). All
changes persist to `fields["sheet"]` in a single `db.update_entity()` call.

### Phase 32 -- Homebrew Monster Builder

**Status: Planned.**

New `HomebrewScreen` accessible from the Monster Reference screen. Full stat
block editor: name, CR, creature type, ability scores, AC, HP, speed, attacks
(name / bonus / damage), special abilities (name / description). Saves to
`data/homebrew_monsters.json` alongside `data/monsters.json`. `srd.py`
loads both files at import time and merges them; `MONSTERS` list contains
SRD + homebrew. Homebrew monsters are marked with a `"source": "homebrew"`
key so they can be filtered or deleted from the builder screen.

### Phase 33 -- Faction Reputation

**Status: Planned.**

`fields["reputation"]` added to faction entities: an integer score (default
0) and a `reputation_log` list of `{date, delta, reason}` entries. Faction
detail screen gains a reputation bar (color-coded: green positive, red
negative) and a scrollable log. New `AdjustReputationScreen` (from faction
detail) lets the DM enter a delta (+/-) and a reason; persists to the log.
`PartyOverviewScreen` gains a Faction Standing section showing all factions
with their current score color-coded. All reputation logic in a new
`reputation.py` module.

### Phase 34 -- Notes & Tag Browser

**Status: Planned.**

`#tag` tokens parsed from note text across all entity types (plain Python
regex, no schema change). New `tags.py` module: `extract_tags(text)` returns
a sorted deduplicated list; `entities_by_tag(tag)` queries all notes for
matches. New `TagBrowserScreen` (`#` key on dashboard): left panel lists all
tags sorted by frequency; selecting one shows matching entities in a right
panel. Clicking an entity opens its `EntityDetailScreen`. `QuickCaptureModal`
gains tag autocomplete (beyond entity names) when the user types `#`.
