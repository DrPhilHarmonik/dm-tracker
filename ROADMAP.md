# DM Tracker Roadmap — Character Sheets, Combat, Dice, Effects

Living plan for the next major phase of work: full D&D 5e character sheets for
Adventurers and Enemies, a dice-rolling engine tied to those sheets, a
round-based combat tracker, and timed stat-changing effects (potions, magic
weapons, buffs/debuffs).

## TUI Review Passes

See `CLAUDE.md` for the full process (screenshot-based visual review, since
the automated test suite drives screens programmatically and never actually
renders them). First full pass done 2026-06-21: caught and fixed a critical
bug (editing any entity's flat fields silently wiped its sheet/active
effects/combat data), a mid-combat data-loss risk (Start Encounter resettable
while already running), a flat/nested level-CR desync, an unstyled ListView,
and oversized number inputs across three screens. Do another full pass after
Phase 11 lands, and a targeted pass on any screen touched in between.

## Confirmed design decisions

- **Ruleset:** D&D 5e (SRD) — six ability scores, proficiency bonus, skills,
  saving throws, AC, HP, standard classes/races.
- **Entity model:** NPCs keep their current lightweight, social-focused
  schema (race, role, alignment, status, location). A new **Enemy** entity
  type holds the full combat stat block (CR, AC, HP, abilities, attacks,
  resistances, etc.) — closer to a monster manual entry. Adventurers get the
  full stat block too, since they're played in combat.
- **Hostile NPCs (BG3-style):** an NPC never mutates into an Enemy in place.
  Instead, a "Make Hostile" action creates a linked Enemy record (cloning
  name/race) and connects it back to the source NPC via a relationship (e.g.
  `hostile form of`). The original NPC record is untouched; the Enemy is what
  actually fights.
- **Ability score generation (wizard):** Standard Array (15/14/13/12/10/8),
  assigned by the DM during character creation.
- **Time/tick system:** round-based only, and scoped to an active encounter.
  Effect durations are counted in rounds. Nothing decays automatically
  outside of combat — between sessions, the DM can manually clear or extend
  effects.

## Open questions per phase

These need a decision when we get to that phase, not now:

- **Phase 1:** exact skill/language/sense lists; how much is auto-derived
  (e.g. proficiency bonus from level/CR) vs. manually entered.
- **Phase 2:** how roll results are surfaced (inline toast vs. a persistent
  roll-log panel); whether to keep roll history per session.
- **Phase 3:** exact UX for "Make Hostile" (button on NPC detail screen) and
  for adding/removing combatants mid-encounter.
- **Phase 4:** effect modifier shape (flat bonus vs. multiplier vs. advantage
  flag), stacking rules for multiple effects on the same stat, whether
  effects can target non-ability stats (AC, speed, attack rolls).
- **Phase 5:** how much the wizard guides vs. offers "use class defaults"
  shortcuts to skip steps.

## Phases

### Phase 1 — Character Sheet Data Model (foundation, blocks everything else)

- Extend `models.py` with a proper 5e character sheet schema for
  `adventurer` and a new `enemy` entity type:
  - Abilities: STR/DEX/CON/INT/WIS/CHA (scores; modifiers derived, not
    stored)
  - Combat: AC, HP (current/max/temp), hit dice, speed, initiative bonus
  - Proficiency bonus (derived from level for adventurers, CR for enemies)
  - Saving throw proficiencies, skill proficiencies (+ expertise)
  - Senses, languages
  - Adventurer-only: class, level, background
  - Enemy-only: CR, creature type, attacks/actions list, legendary actions,
    resistances/immunities/vulnerabilities
- Move away from the flat `EntityFormScreen` field list for these two types —
  a 30-field flat form doesn't scale. Build a dedicated, sectioned character
  sheet screen (likely `TabbedContent`: Abilities / Combat / Skills /
  Attacks) for adventurer and enemy editing specifically. NPC, Location,
  Quest, etc. keep using the existing generic form.
- DB: character sheet data still lives in the existing `fields` JSON column,
  just with a richer, nested shape (e.g. `fields["abilities"] = {"str": 15,
  ...}`) rather than flat strings.
- Tests: schema round-trip (create/update/get an adventurer & enemy with full
  sheet data), modifier derivation math.

### Phase 2 — Dice Rolling Engine

- New `dice.py` module: parse standard notation (`1d20+5`, `2d6`, `4d6kh3`
  for the wizard's roll-stats option later), roll via `random`, return total
  + per-die breakdown for display.
- Stat-aware rolls built on top of the parser: ability checks, saving
  throws, skill checks (score modifier + proficiency bonus if proficient),
  attack rolls, damage rolls — all pulling from a character's sheet.
- TUI: a "Roll" action on the adventurer/enemy detail screen opens a picker
  (ability/skill/save/attack) and shows the result.
- Tests: parser edge cases (modifiers, advantage/disadvantage as roll-twice-
  take-best/worst), stat-aware roll totals against known fixtures.

### Phase 3 — Encounter / Combat Tracker

- New `encounters` concept: a combatant list (links to adventurers, enemies,
  and hostile-NPC-derived enemies), initiative order, current round, current
  turn pointer.
- "Make Hostile" action on NPC detail screen → creates linked Enemy, adds to
  an encounter.
- Combat screen: roll/enter initiative, turn order display, HP
  damage/heal input, condition tags (prone, stunned, etc., optionally with a
  round-based duration that plugs into Phase 4's effect engine), next-
  turn/next-round controls.
- Tests: initiative ordering, round/turn advancement, HP bounds (can't go
  below 0 or above max without explicit override for temp HP).

### Phase 4 — Active Effects & Time-Tick System

- New table `active_effects`: entity_id, source label ("Potion of Giant
  Strength"), stat modifiers (JSON), duration in rounds remaining, the round
  it was applied.
- Effective stats = base sheet values + sum of active effect modifiers,
  computed on read — never mutate the base sheet. Dice engine (Phase 2)
  rolls against effective stats, not base.
- Round advancement (from Phase 3's combat screen) decrements all active
  effects for combatants in that encounter; expired effects are removed and
  surfaced ("Potion of Giant Strength wore off on Mira").
- UI: "Apply Effect" action in the encounter/detail screen; active effects
  list shown per combatant.
- Tests: effect decay over N rounds, expiry removal, effective-stat
  calculation with multiple stacked effects.

### Phase 5 — NPC/Adventurer/Enemy Creation Wizard

- Multi-step TUI wizard, separate from the quick "+ Add" form:
  1. Basic info (name, race, alignment, entity type)
  2. Class & level (adventurer) or CR & creature type (enemy)
  3. Ability scores — assign the Standard Array to the six abilities
  4. Derived stats shown live (modifiers, proficiency bonus, suggested base
     AC/HP)
  5. Skill & saving throw proficiencies (defaults suggested by class/CR,
     editable)
  6. Attacks/equipment summary
  7. Review & save
- Reuse this wizard's stat-assignment step for the "Make Hostile" flow from
  Phase 3 (clone NPC → drop into wizard at step 2/3).

### Phase 6 — Polish & Export Integration

- Detail screens render full character sheets in readable sections instead
  of a flat field dump.
- Markdown export includes formatted character sheets and active
  effects/encounter history where relevant.
- CSS cleanup pass: button sizing/spacing across the sheet and roll-picker
  screens is inconsistent (noted during manual Phase 2 testing) and should
  be tightened up.
- Full regression pass across all phases' tests.

## Status

**Phase 1: Done.** New `sheet.py` module holds the 5e math (ability
modifiers, proficiency bonus by level/CR, saving throw and skill bonuses)
and a `normalize_sheet()` that fills in defaults for any sheet missing
fields. New `enemy` entity type added alongside `adventurer`, both backed by
the same nested `fields["sheet"]` JSON shape. A dedicated tabbed
`CharacterSheetScreen` (Abilities / Combat / Skills & Saves / Attacks &
Traits) is reachable from any adventurer/enemy's detail view via the
"Character Sheet" button or `c` key; the entity detail view also renders a
formatted summary of the sheet. `hostile form of` relationship type added in
preparation for Phase 3's NPC→Enemy conversion. 16/16 tests passing.

**Phase 2: Done.** New `dice.py` module: a generic notation parser/roller
(`2d6+3`, `4d6kh3`/`kl3` for keep-highest/lowest, signed multi-term
expressions) plus 5e-aware wrappers (`roll_d20` with advantage/disadvantage,
`roll_ability_check`, `roll_saving_throw`, `roll_skill_check`, `roll_attack`,
`roll_damage`) that pull bonuses straight from a normalized sheet via
`sheet.py`. A `RollPickerScreen` (reachable from any adventurer/enemy's
detail view via the "Roll Dice" button or `k` key) offers four tabs —
Ability/Save, Skills, Attacks, Custom — each rollable with
advantage/disadvantage toggles where relevant, with an in-session roll
result + history log (not persisted to DB; resets when the screen closes,
per the roadmap's "no persistent roll log" scope decision). 29/29 tests
passing.

**Phase 3: Done.** New `combat.py` module holds pure encounter-state logic
(add/remove combatant, set initiative, start encounter, next turn/round with
condition ticking and expiry) — HP itself is never duplicated, it's always
read/written straight from the combatant's own character sheet so there's
one source of truth. New `encounter` entity type (dashboard grid bumped to
3x3 to fit all 9 types now). A `CombatTrackerScreen` (Combatants / HP &
Conditions / Turn Controls tabs, plus an always-visible roster summary with
a `->` marker on whoever's turn it is) is reachable from any encounter's
detail view via the "Combat Tracker" button or `o` key. NPCs got a "Make
Hostile" action (`h` key) that clones them into a linked Enemy via the
`hostile form of` relationship — the original NPC is never mutated. 44/44
tests passing.

Fixed one real bug along the way: `Select.set_options()` always resets the
widget's selection (it's documented behavior, not a quirk), so refreshing
the combatant dropdowns after every action was silently wiping whichever
combatant the DM had selected — meaning a second sequential action (e.g.
adding a 2nd condition, or removing one) would silently no-op. Fixed by
capturing and restoring the selected value around every `set_options()`
call when it's still valid.

**Phase 4: Done.** New `effects.py` module: active effects (potions, buffs,
magic items) live in an entity's `fields["active_effects"]` list, never
baked into the base sheet. Scope decision: effects modify the six abilities,
AC, or speed (covers "potion of strength," "ring of protection," "boots of
speed"); multiple effects on the same stat simply stack additively — no
attempt to replicate 5e's same-named-bonus rules. `apply_to_sheet()`
computes an effective sheet on read; the roll picker, combat tracker
(initiative rolls and the AC shown in the roster summary), and the entity
detail view all use the effective sheet now, never the base one. Effects
only decay on combat round-advance (`tick_effects()`, wired into
`CombatTrackerScreen`'s Next Turn/Next Round, matching the round-scoped time
system decided at the start — nothing decays outside combat). Expired
effects are removed and surfaced as a notice (e.g. "Potion of Giant Strength
wore off on Mira Thorn"). New "Effects" screen (`f` key) on any
adventurer/enemy's detail view to add/remove effects. 52/52 tests passing.

Fixed a real, fairly serious bug while wiring the Effects screen's Escape
binding: `app.pop_screen()` silently discards any callback registered via
`push_screen(..., callback=...)` without invoking it — only
`Screen.dismiss()` actually fires it. Every screen using
`Binding("escape", "app.pop_screen", ...)` whose caller expected a refresh
on return (the entity detail view returning from Combat Tracker or Effects,
the entity list returning from detail) was silently never refreshing.
Fixed by adding a shared `DismissableScreen` base class
(`action_dismiss_screen` → `self.dismiss()`) and switching every affected
screen and "Back"/"Cancel" button handler to it.

**Phase 5: Done.** New `classes.py` reference module (the 12 core 5e
classes, hit dice, suggested saving throws) plus `sheet.matches_standard_array()`
and `sheet.suggested_ac()`. A `WizardScreen` in `app.py` supports all three
entity types with two modes:

- **NPC**: single Basic Info step (race/role/alignment/status/location) ->
  Review & Create. Quick and Advanced collapse to the same thing since NPCs
  carry no stat block.
- **Adventurer/Enemy, Quick mode**: Basic Info -> Class & Level (or CR &
  Creature Type) -> Standard Array ability scores -> Review & Create (shows
  suggested AC/HP, editable before saving) -> drops straight into the
  Character Sheet screen to fill in skills/attacks afterward.
- **Adventurer/Enemy, Advanced mode**: same as Quick, plus inline Skills &
  Saving Throws and Attacks & Traits steps before Review, so the whole
  character is complete by the time it's created.

Saving throws are suggested from the class's two SRD save proficiencies and
editable; ability scores are validated as a true Standard Array permutation
(reset-to-default button included) rather than letting the DM type any six
numbers. Entry point is two new buttons ("Quick Wizard" / "Advanced Wizard")
on every entity list screen. "Make Hostile" (Phase 3) now routes through the
wizard in Enemy/Quick mode, prefilled from the source NPC, rather than
eagerly creating a bare Enemy before any stats exist — cancelling out of the
wizard leaves no orphaned entity. 61/61 tests passing.

**Export/import upgrade: Done** (pulled forward from Phase 6, requested
mid-Phase-5). Markdown export now has an `include_stats` toggle (Switch on
the Export screen, default on): when enabled, each adventurer/enemy's full
character sheet and active effects are written as structured YAML in the
frontmatter (the single source of truth for round-tripping) plus a
human-readable "## Character Sheet" prose section showing *effective*
(buffed) stats — never the reverse, so re-importing never accidentally
bakes a temporary buff into the permanent sheet. New `export.import_vault()`
parses a vault this app produced (frontmatter + Notes + Relationships
sections) back into entities and relationships; wired into the Backup &
Restore screen alongside the existing JSON path, with the same
non-empty-database guard. Explicitly scoped to vaults this app wrote, not
arbitrary hand-authored Obsidian vaults. 68/68 tests passing.

Next up: **Phase 6** (remaining polish) — the deferred button-sizing CSS
cleanup and a full regression pass.

## Forward Plan

### Phase 6 — Polish & Stability

Goal: tighten the current feature set before adding another major workflow.

- **CSS/layout cleanup:** standardize action rows, button widths, form
  spacing, status messages, and long tab layouts across sheet, roll picker,
  combat, wizard, export, and backup screens.
- **Full regression pass:** run the existing suite after each cleanup pass and
  do a manual smoke test of the core TUI flows: create entity, wizard create,
  edit character sheet, roll dice, apply effect, run combat, export/import,
  backup/restore.
- **Error messaging pass:** keep broad UI-level exception handling for display,
  but make the underlying export/import/backup failures more specific
  (validation error, missing path, parse error, permission/filesystem error).

**Status: Done.** CSS cleanup landed earlier (standardized action-row/button
patterns, consolidated status-message rules across sheet, roll, combat,
wizard, export, and backup screens). New `screens/common.format_io_error()`
categorizes export/import/backup failures (JSON parse, YAML parse,
permission, missing path, is-a-directory, generic validation, generic
filesystem) instead of showing raw exception text for all of them; wired
into all four failure points in `screens/backup.py`. Full regression pass:
76/76 tests green, plus an end-to-end headless smoke run through every core
flow in one continuous session (quick-add → wizard create → character sheet
edit → roll → apply effect → run a combat round → export → JSON backup →
vault re-import with replace) confirming state carries correctly across all
of them.

### Phase 7 — Maintainability Refactor

Goal: make future features cheaper by reducing `app.py` from one large module
into screen-focused modules without changing behavior.

- Extract shared UI pieces first: `DismissableScreen`, palette, common
  status/error helpers, and select-option preservation helpers.
- Split screens by feature area:
  - `screens/dashboard.py`
  - `screens/entities.py`
  - `screens/sheet.py`
  - `screens/dice.py`
  - `screens/combat.py`
  - `screens/effects.py`
  - `screens/wizard.py`
  - `screens/backup.py`
- Keep the first pass mechanical: move code, update imports, run tests. Avoid
  behavioral cleanup until the moved code is stable.
- Add focused tests around any helper extracted from screen code.

**Status:** First mechanical split complete. `app.py` now only owns the app
root and imports `Dashboard`; screen code lives under `screens/` by feature
area (`dashboard`, `entities`, `sheet`, `roll`, `combat`, `effects`,
`wizard`, `backup`, `modals`, `common`). The split intentionally preserved
behavior and used local imports where needed to avoid screen-navigation import
cycles. Existing regression tests and a headless Textual screen-mount smoke
pass both succeed.

### Phase 8 — UI Interaction Tests

Goal: cover the Textual behavior that pure unit tests cannot catch.

- Add Textual pilot tests for screen callback and dismissal behavior, since
  this has already produced real bugs.
- Cover wizard cancellation, "Make Hostile" cancellation, dropdown refreshes
  after combat actions, effect add/remove refreshes, and backup/export button
  status updates.
- Add a small end-to-end happy path using a temporary `DM_DB_PATH`: create an
  adventurer, assign sheet values, roll, apply an effect, add to combat, export
  a vault.

**Status: Done.** Five new test files drive the real `DMApp` through a
headless `Pilot` session (no `pytest-asyncio` dependency added — each test
wraps an inner `async def scenario()` in a plain `asyncio.run()` call):

- `test_ui_dismissal.py` — escaping Entity Detail refreshes the caller list,
  escaping Combat Tracker/Effects refreshes the caller detail, and a direct
  regression for the `Select.set_options()` selection-wiping bug (add two
  conditions in a row to the same combatant and confirm both land).
- `test_ui_wizard.py` — Escape mid-wizard creates nothing; "Make Hostile"
  declined creates nothing; "Make Hostile" confirmed then cancelled out of
  the wizard leaves no orphaned Enemy or relationship; wizard buttons appear
  only for npc/adventurer/enemy (the Phase 8 prep work caught and fixed that
  exact gap one conversation turn before writing this).
- `test_ui_backup.py` — Export/Backup/Restore screens' status Statics
  actually update on both success and categorized-failure paths, and the
  vault-replace confirmation dialog blocks the import until confirmed.
- `test_ui_e2e.py` — one continuous session: wizard-create an adventurer →
  edit its character sheet → roll (confirms it reads the saved sheet) →
  apply an effect → run a combat round (confirms HP/AC/effect carried
  through) → export a vault (confirms the file reflects all of the above).

93/93 tests passing; the UI suite adds roughly 24s to a previously
sub-second run (10 pilot tests each booting a real Textual event loop) —
acceptable for the regression coverage gained.

### Phase 9 — Data Integrity Layer

Goal: prevent invalid campaign data from entering through UI, CLI, import, or
future automation.

- Validate entity type and relationship type in `db.create_entity()`,
  `db.update_entity()`, and `db.create_relationship()`.
- Add schema-level validation for known flat fields and sheet/effect/combat
  shapes before persistence.
- Consider a thin service layer for higher-level operations such as hostile
  conversion, combat mutations, backup restore, and vault import so the UI is
  not responsible for maintaining invariants.
- Add tests for invalid types, malformed JSON-shaped fields, missing
  relationship targets, and replace/import edge cases.

**Status: Done.** `db.py` is the single chokepoint every write path already
goes through (UI/wizard, CLI flags, JSON restore, vault import all end up
calling `create_entity`/`update_entity`/`create_relationship`/`replace_all`),
so validation landed there instead of a separate service layer -- the
"consider a thin service layer" idea turned out unnecessary once the
existing chokepoint was hardened.

- `validate_entity_type()` / `validate_relationship_type()`: reject anything
  not in `models.ENTITY_TYPES` / `RELATIONSHIP_TYPES`.
- `validate_fields()` (used by `create_entity`/`update_entity`, the live
  single-entity paths): rejects unknown flat field keys and out-of-range
  select/number values for the entity's type, then normalizes the
  `sheet`/`active_effects`/`combat` sub-shapes via the existing
  `sheet.normalize_sheet()`/`effects.normalize_effects()`/
  `combat.normalize_combat()` (deliberately lenient about missing keys).
- `normalize_special_fields()` (used by `replace_all`, the bulk-import
  path): only normalizes the sub-shapes, intentionally skipping the strict
  flat-field checks so restoring an older backup whose schema has since
  changed doesn't fail on fields that were valid when it was taken.
- `replace_all` validates every entity/relationship *before* deleting
  anything, so a bad import raises without wiping existing data.
- `update_entity` now raises if the id doesn't exist (was previously a
  silent no-op affecting 0 rows); `create_relationship` now checks both
  endpoints exist before insert, with a clean message instead of a raw
  `sqlite3.IntegrityError` leaking from the FK constraint.

New `tests/test_db_validation.py` (20 tests) covers every rejection path
plus the "doesn't wipe existing data on a bad import" and "bulk import
stays lenient about deprecated fields" behaviors. Manually verified the
full chain end-to-end: a JSON backup with an invalid entity type surfaces
as "Validation error: Unknown entity type: ..." in the Backup & Restore
screen, not a raw traceback. 113/113 tests passing.

### Phase 10 — Session Workflow

Goal: build the next user-facing workflow on top of the stable core.

**Scope-checked decisions (resolved before estimating/building):**

- **Notable NPCs** = NPCs with a relationship (either direction) to an active
  quest or active encounter. Not "most relationships overall," not
  "recently edited" — tied to what's actually relevant tonight.
- **Active encounters** = status `Planned` or `Active` (a DM prepping wants
  to see what they're about to run, not just what's mid-fight).
- **Session notes linking to entities** = reuse the Session entity's
  existing `notes` field. DM types `[[Entity Name]]` by hand, same
  convention already used by the vault export. No new schema, no new
  note-taking mechanic.
- **"Unresolved relationships"** — dropped. Nothing in the current data
  model captures a resolved/unresolved state, and no concrete need has
  shown up to justify inventing one.
- **v1 scope** = a new read-only `SessionWorkflowScreen` (reachable from a
  Session entity's detail view) that aggregates and displays the lists
  below, with buttons that *navigate* into screens that already exist
  (Detail / Character Sheet / Roll Dice / Combat Tracker). No new mutation
  logic — marking a quest complete, etc. still happens on the entity's own
  screen, not inline here.
- **Gap-filled without a separate question**: a **Player Characters**
  section listing all Adventurers with Roll/Sheet shortcuts. The roadmap's
  "quick roll/combat actions" bullet implies PCs should be front and
  center; the original bullet list never explicitly included them.

**Sections in the new screen:**
1. Player Characters (all adventurers) → Roll Dice / Character Sheet
2. Active Quests (status=Active) → Detail
3. Active Encounters (status=Planned/Active) → Combat Tracker
4. Notable NPCs (related to #2/#3) → Detail
5. Recent Notes (any entity, non-empty notes, sorted by updated_at) → Detail

No new entity type, no new persisted fields, no new export logic in this
pass — everything is computed from existing data on read. Obsidian export
of the session log specifically was explicitly "optional" in the original
wording and is deferred past v1.

**Revised estimate:** 5 points (down from an initial 8 before scoping —
dropping "unresolved relationships" and simplifying session notes to "just
the existing notes field" removed the two most open-ended sub-features).

**Status: Done.** New top-level `session_workflow.py` module holds the pure
aggregation logic (`player_characters()`, `active_quests()`,
`active_encounters()`, `notable_npcs()`, `recent_notes()`) — no new schema,
everything computed from existing entities/relationships on read, matching
the v1 scope. A `SessionWorkflowScreen` (reachable from any Session's detail
view via the "Session Workflow" button or `w` key) renders the five
sections as separate DataTables: Player Characters (with explicit
"Character Sheet" / "Roll Dice" buttons acting on the selected row, per the
gap-filled PC section), Active Quests, Active Encounters, Notable NPCs, and
Recent Notes — each row navigates straight into the matching existing
screen (Sheet, Combat Tracker, or Detail) rather than introducing any new
mutation UI. 129/129 tests passing.

### Phase 11 — Spellcasting, Action Economy, and Summons

Goal: extend the character sheet and combat tracker to cover three related
gaps that show up once a party past level 1 actually plays a fight: nothing
today tracks what a combatant can still do this turn, nothing tracks spell
slots/spells, and nothing creates a temporary ally creature mid-combat.

**Scope-checked decisions (resolved before estimating/building):**

- **Action economy is tied to specific abilities, not a generic checklist.**
  Each entry in a sheet's `attacks` list (and the new `spells` list below)
  gains an `action_cost` field: `action` / `bonus_action` / `reaction` /
  `free`. The Combat Tracker tracks, per combatant per turn, which of
  Action/Bonus Action/Reaction have been spent; using a tagged attack or
  spell from the tracker auto-marks that slot used. Slots reset when that
  combatant's turn starts (hooks into `combat.py`'s existing next-turn
  logic).
- **Spellcasting = slots + a spell list + cast roll**, mirroring how attacks
  already work. Sheet gains: a `spellcasting_ability` (int/wis/cha, sets
  save DC and spell attack bonus), `spell_slots` (current/max per level
  1-9), and a `spells` list (name, level 0-9 [0 = cantrip, costs no slot],
  `action_cost`, `save_or_attack`: save / attack / none, save ability if
  applicable, freeform effect text — no built-in SRD spell database).
  "Cast Spell" extends the existing Roll Picker / combat attack-roll flow:
  shows save DC or rolls spell attack bonus the same way weapon attacks do
  now, and decrements the matching slot (cantrips never touch slots).
- **Summons are real, persisted entities, not combat-only stubs.** A summon
  creates an actual `adventurer`/`enemy` entity with its own full sheet
  (reusing the existing Quick Wizard flow, the same pattern "Make Hostile"
  already established), linked back to the summoner via a new relationship
  type `summoned by`. From there it's one click to add to the current
  encounter via the Combat Tracker's existing "Add Combatant" picker — no
  new combat-add mechanism needed. Removing a summon when it ends is just
  deleting the entity, same as any other.
- **No new "side" / ally-vs-enemy concept.** The combat tracker doesn't
  track allegiance today (DM tracks that mentally, same as which enemies are
  already hostile); summons don't change that. Not in scope for this phase.

**Open questions for when we build this:**

- Exact `CharacterSheetScreen` layout for the new Spells tab (likely a
  fifth tab alongside Abilities/Combat/Skills & Saves/Attacks & Traits,
  following the same add/remove-via-ListView pattern as Attacks).
  whether the cast-roll UI lives in the existing Roll Picker's Attacks tab
  (extended to cover spells too) or a new dedicated tab.
- Whether "Make Hostile"'s wizard-prefill code can be generalized into a
  shared "spawn linked entity" helper that both it and Summon call, or
  whether summons need enough of their own prefill logic (CR/level
  suggestions from the summoning spell, e.g. "Conjure Animals" tier) to stay
  separate.

**Estimate:** 8 points — three sub-features, each touching the sheet schema,
`sheet.py`'s derived-stat math, at least one screen's UI, and tests; action
economy and spellcasting are tightly coupled (both ride on `action_cost`)
so they're cheaper together than the points would suggest in isolation,
which is offset by summons needing its own entity-creation flow end to end.

**Status:** Scoped, not started. Next up after Phase 10 (Session Workflow),
unless reprioritized.

### Phase 12 — Defined Races with Integrated Stat Bonuses

Goal: let an Adventurer's race actually affect their numbers (ability
scores, speed, senses, languages) instead of "race" being a flavor-only
text field, the same way class/level already feeds AC/HP suggestions in the
wizard.

**Scope-checked decisions (resolved before estimating/building):**

- **Race list = core SRD races + subraces**, all SRD-legal (no PHB-only
  content like Drow, consistent with the project's existing "D&D 5e (SRD)"
  ruleset decision): Human, Elf (High Elf, Wood Elf), Dwarf (Hill Dwarf,
  Mountain Dwarf), Halfling (Lightfoot, Stout), Gnome (Forest Gnome, Rock
  Gnome), Half-Elf, Half-Orc, Dragonborn, Tiefling — 13 selectable
  race/subrace entries.
- **Bonuses bake into the Standard Array at creation time**, not a live
  modifier. Matches how the wizard already turns class+level into a
  suggested AC/HP; simplest mechanism that satisfies "stats are
  integrated." Changing an existing character's race later is a manual
  edit (same as today), not a re-derivable toggle — no live recompute
  machinery added to `sheet.py` for this.
- **A race definition carries:** ability score bonuses, speed (only a few
  races deviate from 30 ft., e.g. Dwarf/Halfling/Gnome at 25 ft.), senses
  (e.g. "Darkvision 60 ft."), and languages (e.g. "Common, Elvish"). These
  bake into the sheet's existing `speed`/`senses`/`languages` fields the
  same way ability bonuses bake into `abilities`, at creation time only.
- **Non-numeric racial traits are out of scope.** Things like Dwarven
  Toughness (+1 HP per level), Gnome Cunning (advantage on INT/WIS/CHA
  saves vs. magic), or Stout Halfling's poison resistance don't fit the
  ability/speed/senses/language model and won't be mechanically enforced —
  at most a freeform note, consistent with how `special_abilities` already
  works on the sheet.
- **New Wizard step, adventurer-only.** Enemies use CR/creature type, not
  race, and NPCs have no stat block to bake bonuses into — both keep their
  current schema untouched. New step order: Basic Info → **Race** (select
  from the list) → Class & Level → Standard Array (shown with the race
  bonus already applied) → Review & Create.
- **The flat `race` schema field stays freeform text, unchanged.** Picking
  a race/subrace in the wizard writes its name into that same text field
  (e.g. "Wood Elf") exactly as typing it manually would — no schema change,
  no migration, no constraint added to already-existing characters or
  hand-typed values. The new race list only exists to compute the bonus
  applied during wizard creation.

**Open question for build time:** Half-Elf is the one SRD race with a
player-choice bonus ("+1 to two ability scores of your choice" on top of
+2 CHA) rather than a fixed spread. Worth a small "pick two abilities"
sub-step in the wizard when Half-Elf is chosen, rather than guessing a
default pair — needs a decision when this is actually built, not blocking
the scope.

**New module:** `races.py` (mirrors `classes.py`'s shape) holding the
race/subrace list with each entry's ability bonuses, speed override,
senses, and languages, plus a `apply_race_bonus(abilities, race_key)` -style
helper the wizard calls when assembling the Standard Array step.

**Estimate:** 5 points — one self-contained reference module plus one new
wizard step; smaller than Phase 11 since it's a single feature rather than
three, but the Half-Elf choice-bonus sub-step adds a bit of wizard-flow
complexity beyond a flat lookup table.

**Status: Done.** New `races.py` module (13 SRD-legal race/subrace entries,
mirroring `classes.py`'s shape) plus `apply_bonuses()`/`ability_bonus_total()`
helpers. Wizard gained a new "Race" step (adventurer-only, between Basic
Info and Class & Level) with a live-updating ability-bonus summary; picking
Half-Elf reveals a "choose 2 abilities for +1 each" sub-step, validated to
reject picking the same ability twice. The raw Standard Array assignment in
`self.data["abilities"]` is never mutated -- bonuses are only ever applied
to a derived copy (`_effective_abilities()`) used for the Review step's
AC/HP suggestions and the final sheet, so navigating Back to re-edit ability
scores still validates against the unmodified Standard Array. Speed,
senses, and languages bake in from the chosen race the same way. 144/144
tests passing.

Found and fixed one real bug while building this: the new race Select fires
a `Changed` event on its own initial mount (no-value -> default value), and
the handler was re-entrantly re-rendering the step while the original mount
was still in progress, intermittently corrupting a later step's `Select`
widget (~40% of e2e test runs failed before the fix). Fixed by only
re-rendering when the new value actually differs from the value the step
was built with.

### Phase 13 — Defined Classes (Class-Driven Logic)

Goal: make the class field as structurally meaningful as race became in
Phase 12. `classes.py` already exists with names, hit dice, and suggested
saving throw proficiencies, but that's as far as it goes. Phase 13 extends
it to drive the rest of the class-relevant math the wizard and sheet need,
and lays the groundwork Phase 11's spellcasting system requires.

**Scope-checked decisions (resolved before estimating/building):**

- **Spellcasting ability per class.** Each spellcasting class gets a
  canonical ability (Wizard/Artificer = INT, Cleric/Druid/Ranger = WIS,
  Bard/Paladin/Sorcerer/Warlock = CHA). `classes.py` gains a
  `spellcasting_ability` key (None for non-casters). Phase 11's spell
  attack bonus and save DC will read this rather than asking the DM to
  re-enter it. This is the primary prerequisite for Phase 11; everything
  else in Phase 13 is bonus.
- **Accurate per-level HP calculation in the wizard.** Today the Review
  step shows a rough "d10+2=12" style suggestion. With class hit dice
  already in `classes.py` and race bonuses now baking into CON in Phase 12,
  the wizard can compute proper average HP: (hit_die / 2 + 1) * level +
  (con_modifier * level), the standard 5e average-roll formula. Still
  shown as an editable suggestion, not locked in.
- **Armor and weapon proficiency summary.** Each class entry gains a
  `proficiencies` key: a short freeform string ("Light armor, simple
  weapons, hand crossbows, longswords, rapiers, shortswords") written into
  `sheet["proficiencies"]` at creation time. No mechanical enforcement
  (the app doesn't police which weapons a PC can wield); purely a reference
  note on the sheet. Mirrors how senses/languages bake in from race.
- **Primary ability suggestion.** Each class entry gains a `primary_ability`
  key (e.g. STR for Fighter, DEX or INT for Rogue depending on build).
  Displayed as a hint during the Standard Array assignment step ("Suggested
  primary: STR") -- not enforced, just a nudge so new players know where to
  put the 15.
- **No subclass support.** Arcane Trickster, Eldritch Knight, Battle Smith
  etc. have different spellcasting abilities than their parent class.
  Out of scope for this phase -- a freeform "subclass" notes field is
  sufficient, same as how non-numeric racial traits were handled in Phase 12.

**Open questions for build time:**

- Whether the primary-ability hint in the wizard should be a single ability
  or a list of options (Ranger: DEX or STR; Rogue: DEX or INT for AT).
  Could surface as "DEX or STR" label and let the DM pick, or just list
  the most common default.
- Whether proficiencies should be a freeform string or a structured set of
  tags (for future filtering). A string is simpler and consistent with how
  senses/languages work; tags would let Phase 15's encounter builder
  eventually cross-reference armor class assumptions. Lean toward string
  unless there's a concrete near-term need.

**Estimate:** 3 points -- almost entirely a data-layer and wizard-hint
change, no new screen. The HP formula and proficiency bake-in follow the
same pattern Phase 12 established; the main lift is expanding `classes.py`
and wiring the spellcasting_ability field so Phase 11 can read it.

**Status: Done** (landed silently alongside Phase 12). `classes.py` already
holds `CLASS_SPELLCASTING_ABILITY`, `CLASS_PRIMARY_ABILITY`,
`CLASS_PROFICIENCIES`, and `suggested_hp()`. The wizard's abilities step
shows the primary/spellcasting hint; save is baked from `CLASS_SAVING_THROWS`;
proficiencies bake into `sheet["proficiencies"]` on wizard save.

---

### Phase 14 — Conditions & Death Saves

Goal: replace the combat tracker's freeform condition tags with the full
14 SRD conditions as a proper library, and add death save tracking for PCs
at 0 HP -- two gaps that come up in almost every real combat session.

**Scope-checked decisions (resolved before estimating/building):**

- **Conditions library = the 14 SRD conditions, nothing more.** Blinded,
  Charmed, Deafened, Exhaustion (levels 1-6), Frightened, Grappled,
  Incapacitated, Invisible, Paralyzed, Petrified, Poisoned, Prone,
  Restrained, Stunned, Unconscious. Their mechanical summaries (the SRD
  bullet-point descriptions) are embedded as read-only reference text
  alongside each condition in the picker UI -- so the DM can apply
  "Paralyzed" and immediately see "Incapacitated; fails STR/DEX saves; hits
  against this creature have advantage; attacker within 5 ft. scores a
  crit." New `conditions.py` module holds this table.
- **Conditions integrate with existing active effects duration.** Applying
  a condition from the library goes through the same `active_effects`
  mechanism Phase 4 built, with a duration in rounds (or "until dispelled"
  as a sentinel value). Round advance already ticks effects down and removes
  expired ones -- conditions ride that for free.
- **Mechanical enforcement is reference-only, not enforced.** The app
  doesn't intercept attack rolls against a prone creature and add
  advantage automatically. The condition's text is surfaced as a reminder
  in the combat roster summary; the DM applies the mechanical effects
  themselves. Same philosophy as how resistances/immunities work today.
- **Death saves are tracked per adventurer in the combat tracker only.**
  When a PC's current HP hits 0, the combat tracker surfaces a death save
  section for them: three success checkboxes, three failure checkboxes.
  Checking three successes marks the PC as Stable (0 HP, not dying);
  three failures marks them as Dead (sets a "Dead" condition). A Stable
  marker clears on the next long rest (manual clear by DM). Death save
  state lives in the combat encounter data, not persisted to the sheet
  between sessions (a PC who was stabilized last session starts fresh next
  session, per 5e rules).
- **Enemies do not get death saves.** They go to 0 HP and are marked
  defeated, same as today.

**Open questions for build time:**

- Exhaustion's 6 levels (each cumulative with the previous) are the one
  condition that's a counter rather than a binary flag. Whether to model
  it as a 1-6 spinner alongside the condition application or just let the
  DM apply "Exhaustion" multiple times (stacking in the effects list) is a
  UX judgment call at build time.
- Whether death save results should feed back into the round-advance logic
  (auto-roll a death save die on each of the PC's turns) or stay as
  manual checkboxes. Manual is consistent with how the app handles all
  rolls today (player rolls physical dice; app records the result).

**Estimate:** 5 points -- `conditions.py` is straightforward data, but
wiring it into the combat tracker UI (condition picker replacing freeform
input, roster summary showing condition names with reference text on hover,
death save section appearing/disappearing based on HP state) is a real
screen-layout change touching three of the four combat tracker tabs.

**Status: Done.** New `conditions.py` holds all 15 SRD conditions (Exhaustion
included) with 1-2 sentence mechanical summaries. The combat tracker's
freeform condition Input is replaced by a `Select` picker; selecting a
condition immediately shows its description in blue below the dropdown.
"Custom..." option reveals a text Input for homebrew/unlisted conditions.
Death save tracking appears automatically when a combatant is an Adventurer
at 0 HP: + Success / + Failure buttons track the count; 3 successes applies
"Stable" and resets, 3 failures applies "Dead" and resets. Enemy entities
never show the death save section. `combat.py` gains `add_death_save()` and
`reset_death_saves()`; `normalize_combat()` backfills `death_saves: {successes,
failures}` on old combatant records. Exhaustion treated as a regular
condition (apply multiple times to stack levels). 19 new tests.

---

### Phase 15 — Encounter Balance Calculator

Goal: help the DM know whether the fight they're building is going to be
trivial or a TPK before the players sit down. The DMG's encounter difficulty
math is pure arithmetic on CR/XP values the SRD fully publishes -- no
copyright concern, and no new data beyond what the app already tracks.

**Scope-checked decisions (resolved before estimating/building):**

- **Difficulty shown live in the Combat Tracker's Combatants tab as enemies
  are added.** The DM adds enemies to the encounter the same way they do
  today; the balance calculation is a live readout that updates with each
  add/remove, not a separate planning screen.
- **Math follows the DMG XP budget method.** Each CR maps to an XP value
  (full SRD table). Enemy XP is summed, then multiplied by the encounter
  multiplier (x1 for 1 enemy, x1.5 for 2, x2 for 3-6, x2.5 for 7-10,
  x3 for 11-14, x4 for 15+). Party XP thresholds are the four-tier table
  from the DMG (Easy/Medium/Hard/Deadly per character level), summed across
  all adventurer combatants in the encounter. Difficulty rating = which
  threshold the adjusted XP falls above. New `encounter_balance.py` module
  holds these lookup tables and the calculation.
- **Only enemy CR and adventurer level are needed.** Both are already
  on each entity's sheet -- no new fields, no new input from the DM.
  Enemies without a CR (e.g. summons, NPCs-turned-enemies without a filled
  sheet) are excluded from the calculation with a note ("N/A -- missing
  CR").
- **No "build an encounter" planning mode.** The calculator answers "how
  hard is this specific encounter I'm currently setting up" -- it doesn't
  offer to generate a balanced encounter from scratch. That's a bigger
  feature and a different workflow.

**Open questions for build time:**

- Where exactly the difficulty readout lives in the Combatants tab layout.
  Below the combatant list and above the Add Combatant controls seems
  natural, but the tab is already fairly full; may need to collapse the
  readout to a single line ("Difficulty: Hard (4,200 / 3,900 threshold)")
  that expands on focus.
- Whether to show per-enemy XP values in the combatant list rows alongside
  HP, or keep the list minimal and put all XP detail in the summary line.

**Estimate:** 3 points -- the lookup tables and math are simple; the main
work is fitting the readout cleanly into the existing Combatants tab UI
without cluttering it, and writing tests for the XP multiplier edge cases.

**Status: Done.** New `encounter_balance.py` module holds the full SRD CR-to-XP
table (CR 0 through CR 30), DMG per-character level thresholds (Easy/Medium/Hard/
Deadly for levels 1-20), and DMG encounter multipliers by enemy count. The
Combatants tab gains a live `#balance-readout` widget that updates on every
add/remove: shows difficulty label in matching color (green/yellow/orange/red),
adjusted XP with multiplier, and the next threshold to watch. Enemies missing a
CR are excluded from the calculation with a count note. 15 new tests.

---

### Phase 16 — Character Import (D&D Beyond & Structured Formats)

Goal: let a DM import their existing campaign characters without hand-
entering every field, by reading structured data formats the DM already
owns and controls -- not copyrighted source material, but their own
character and campaign data.

**Scope-checked decisions (resolved before estimating/building):**

- **D&D Beyond character JSON export is the primary target.** D&D Beyond
  lets any user export their own character as a JSON file from the
  character sheet page. That JSON is the user's own campaign data; importing
  it raises no copyright concerns. The importer maps D&D Beyond's ability
  scores, class, level, HP, AC, speed, skills, and saving throw
  proficiencies into the app's `fields["sheet"]` shape. Flavor text
  (backstory, personality traits, bonds) maps to the entity's notes field.
- **A simple CSV template is the secondary target.** For batch-adding NPCs,
  locations, or enemy rosters without a D&D Beyond source: a documented
  CSV schema (name, type, field columns matching the entity's flat schema)
  that the DM can fill in from any spreadsheet and import in one shot.
  The export screen already produces Markdown; the import screen (Backup &
  Restore, which already handles JSON and Vault imports) gains a third path:
  "Import CSV."
- **Import is additive, never destructive.** Importing a D&D Beyond
  character always creates a new Adventurer entity; it never overwrites an
  existing one even if the names match. Same policy the Vault importer
  already follows. Duplicate detection (warn if a same-named entity already
  exists) is a courtesy, not a block.
- **Roll20 and other VTT export formats are out of scope for this phase.**
  Roll20's export format is less stable and less cleanly structured than
  D&D Beyond's; adding it is a separate, incremental extension once the
  D&D Beyond path is proven. The CSV template covers the "any VTT" case
  adequately for now via a manual export-and-reformat step.
- **The importer lives in a new `importers/` sub-package.** `importers/ddb.py`
  (D&D Beyond JSON -> entity dict), `importers/csv_import.py` (CSV row ->
  entity dict), both returning the same intermediate shape that a shared
  `import_entity()` function hands to `db.create_entity()`. Keeps the
  format-specific parsing out of `db.py` and out of the UI layer.

**Open questions for build time:**

- D&D Beyond's JSON schema has changed format at least twice since launch.
  Whether to target the current export format only, or build a thin version-
  detection layer that handles the last two formats, is a pragmatic call
  at build time (probably: handle current format, log a clear error for
  anything that looks like an older shape).
- Whether imported characters should land directly in the Character Sheet
  screen (same as the Quick Wizard's "Quick mode drops into sheet") or
  in the entity detail view, so the DM can review before editing. Probably
  the detail view, since import implies "done" not "continue filling in."

**Estimate:** 6 points -- the D&D Beyond JSON mapping is the bulk of the
work (their schema is wide; mapping it faithfully requires reading the
format carefully and handling optional/missing fields gracefully), plus
the CSV parser, the import UI path in Backup & Restore, and tests for
both import paths against fixture files.

**Status: Done.** New `importers/` package: `__init__.py` holds the shared
`import_entity()` function (always additive, warns on duplicate names, never
overwrites); `ddb.py` parses D&D Beyond character export JSON (with and without
the `"data"` wrapper), mapping abilities, class/level, HP, AC, speed, race,
notes, skill proficiencies (via skills[].value), and baking in class data from
`classes.py`; `csv_import.py` handles a unified-header CSV covering all entity
types in one file (adventurers and enemies get sheet columns auto-assembled;
NPCs/locations use flat fields; Download Template writes a commented example).
Both importers are wired into Backup & Restore with new Import D&D Beyond
Character and Import CSV sections. Fixture files in `tests/fixtures/`. 23 new
tests, 216 total.

---

### Phase 17 — Multi-Campaign Support

Goal: make the app a first-class multi-campaign tool instead of a
single-database tool the DM has to manage by hand via environment variable.
A DM running two concurrent campaigns (e.g. a homebrew and a published
adventure) should be able to switch between them in the app without touching
the shell.

**Scope-checked decisions (resolved before estimating/building):**

- **Each campaign is a separate SQLite database file**, same as today.
  The switch is purely which file the app points at -- no schema changes,
  no data migration, no merged-campaign concepts.
- **A campaign switcher lives on the Dashboard.** The top of the Dashboard
  shows the current campaign name and a "Switch Campaign" button. The
  switcher screen lists saved campaigns (name, last-opened date, entity
  count as a quick summary), with options to open, create new, rename, or
  delete. Creating a new campaign runs `db.init_db()` on a new file and
  opens it immediately.
- **Campaign metadata (name, created date) lives in a small `campaigns`
  table in a separate manager database**, not in each campaign's own DB.
  Location: `~/.local/share/dm_tracker/campaigns.db` (XDG data dir),
  separate from any individual campaign file. This avoids "campaign
  Strahd Run knows its own name" awkwardness and means renaming a campaign
  in the manager is a one-row update that doesn't touch the campaign data.
- **DM_DB_PATH env override still works** for power users and scripts.
  When set, the app opens that file directly and skips the switcher, same
  as today. The switcher is additive, not a replacement.
- **No cross-campaign data sharing.** NPCs, locations, and other entities
  are scoped to their campaign. There is no "shared NPC pool" or
  cross-campaign relationship. If a DM wants the same recurring villain in
  two campaigns, they create two entities.

**Open questions for build time:**

- Where campaign files live by default (when not using DM_DB_PATH). Options:
  `~/.local/share/dm_tracker/<campaign-name>.db` (XDG standard),
  `~/dm_campaigns/<name>.db` (visible/portable), or alongside the app
  source. XDG is most correct; a first-run prompt asking where to store
  campaigns would cover the "I want them on a shared drive" case.
- Whether the Dashboard's campaign switcher should show a "last session"
  summary (most recent session entity's name and date) as a quick-context
  reminder of where each campaign left off.

**Estimate:** 5 points -- the manager DB + switcher screen is new surface
area, but the campaign-open logic is a thin wrapper around existing
`db.init_db()` / `db.DB_PATH` machinery. The main complexity is the
first-run flow (no campaigns yet -> prompt to create one) and making sure
the switcher screen dismisses cleanly and re-mounts the Dashboard with the
new campaign's entity counts.

**Status: Done.** New `campaign_manager.py` handles the registry DB at
`~/.local/share/dm_tracker/campaigns.db`; campaign files default to
`~/.local/share/dm_tracker/campaigns/<name>.db`. `db.set_db_path()` switches
the active DB at runtime via env var. App startup auto-creates "My Campaign"
on first run if none exist; `DM_DB_PATH` still bypasses the manager entirely.
Dashboard title shows "DM Tracker -- <campaign name>"; new "Switch Campaign"
button and `^w` hotkey open the CampaignSwitcherScreen (DataTable with name,
last opened, entity count, path; Open/Rename/Delete + Create Campaign).
Rename is registry-only (file untouched); Delete removes from registry without
deleting the file. 18 new tests, 234 total.

---

### Phase 18 — In-Session Quick Capture

Goal: let the DM log something that just happened at the table in under
three keystrokes, without navigating away from whatever screen they're
currently on (usually the combat tracker or a character sheet).

**Scope-checked decisions (resolved before estimating/building):**

- **Global hotkey (`^n` -- Ctrl+N) opens a Quick Capture overlay from
  anywhere in the app.** The overlay is a small modal (similar to the
  existing Confirm dialog) with a single text input. The DM types a note
  and presses Enter; the overlay dismisses and returns them to exactly
  where they were. No navigation, no mode change.
- **Captured notes append to the active session entity's notes field.**
  "Active session" = the most recently created or last-opened Session
  entity. If no Session entity exists, a brief inline prompt asks the DM
  to either create one or pick an existing one; after that, the preference
  is remembered for the rest of the app session (not persisted to DB).
- **Optional entity tag.** Before pressing Enter, the DM can press Tab to
  reveal a second field: "Tag to entity (optional)." Typing a partial name
  and pressing Enter appends the same note to that entity's notes as well
  as the session. This covers "I need to remember that Gareth the merchant
  offered us a deal" -- the note lands on both the session and Gareth's
  entity. The tag field autocompletes from existing entity names.
- **No new entity type, no new DB table.** Every captured note is plain
  text appended to an existing entity's notes field via `db.update_entity()`,
  with a lightweight timestamp prefix ("Round 4: ...") when captured during
  an active encounter. The existing notes field is already a freetext blob;
  this just provides a faster path to appending to it.
- **"Round N:" prefix is automatic when a combat is active.** The Quick
  Capture overlay checks whether a CombatTrackerScreen is currently in the
  screen stack; if so, it reads the current round number and prefixes the
  note with it. If not, no prefix (or a bare timestamp if the DM prefers
  -- open question).

**Open questions for build time:**

- Whether the timestamp/round prefix should be configurable (round number
  only, wall-clock time only, both, none) or just hardcoded to round number
  during combat and nothing outside.
- Whether "Tag to entity" should support tagging multiple entities in one
  capture (e.g. both the merchant and the quest he's offering), or stay
  as a single-entity tag per capture to keep the overlay minimal. Single
  tag is probably right for v1.

**Estimate:** 4 points -- the overlay itself is small, but detecting
"active session" reliably (what if the DM hasn't opened a Session entity
yet?), wiring the entity autocomplete, and inserting the round-prefix
cleanly around the combat tracker's screen-stack state adds enough edge
cases to warrant care.

**Status: Done.** `screens/quick_capture.py` -- `QuickCaptureModal` opens
from `ctrl+n` anywhere in the app. Clean one-field overlay: header shows
current round and session name; Enter saves; Tab reveals a live-filtered
entity tag field (autocomplete from all entities, up to 10 matches). Note
appends to the active session's notes field; if a tag entity is also selected,
appends there too. If no session exists, warns and requires an entity tag to
save. On save, a toast notification confirms where the note landed.
Round prefix (`[Round N] `) is auto-injected when a CombatTrackerScreen is
in the screen stack; omitted otherwise. `db.latest_session()` picks the most
recently created session; active session is cached on the App object for
the rest of the run. 14 new tests, 248 total.
