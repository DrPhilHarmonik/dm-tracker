# DM Tracker Roadmap — Character Sheets, Combat, Dice, Effects

Living plan for the next major phase of work: full D&D 5e character sheets for
Adventurers and Enemies, a dice-rolling engine tied to those sheets, a
round-based combat tracker, and timed stat-changing effects (potions, magic
weapons, buffs/debuffs).

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
