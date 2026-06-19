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

Next up: **Phase 2** (dice rolling engine), which reads ability scores and
proficiency bonus off this same sheet shape.
