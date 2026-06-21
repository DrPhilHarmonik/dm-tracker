# DM Tracker — project instructions

## TUI Review Passes

This is a Textual TUI app. Automated tests drive screens via `pilot.press()` /
direct `action_*()` calls, which exercise logic but bypass rendering entirely
— a button can be visually collapsed, unstyled, or stacked in the wrong
direction and every test still passes. Two real bugs were only caught by
actually looking at a rendered screen: action-button rows silently stacking
vertically instead of horizontally (wrong container widget), and a ListView
rendering with no background/border because one screen's CSS rule was
missing it.

**Whenever a change touches a screen's `compose()`/CSS (new widget, layout
change, new screen), do a visual pass before considering the work done — not
just a green test suite:**

1. Boot the app headlessly and navigate to the affected screen(s), the same
   way `tests/test_ui_*.py` already does:
   ```python
   app = DMApp()
   async with app.run_test(size=(140, 50)) as pilot:
       await pilot.pause()
       await pilot.press("a")          # or whichever screen
       ...
       app.save_screenshot("/tmp/ui_pass/01_some_screen.svg")
   ```
2. Convert to PNG and view it:
   ```python
   from dev.tui_screenshot import svg_to_png
   svg_to_png("/tmp/ui_pass/01_some_screen.svg")
   ```
   Then `Read` the resulting PNG.
3. For each visible component, check: is the widget type right for the
   value (Select vs. Switch vs. Input; a 1-2 digit number doesn't need a
   full-width Input), is it sized/placed the way a DM would expect, and does
   it actually do what its label says (e.g. footer hotkeys shouldn't be
   shown for actions that don't apply to the current entity type).
4. Fix what's clearly wrong. For subjective layout calls (more compact
   skill list, grouping sub-forms with borders, etc.), flag them rather than
   silently redesigning — these are judgment calls for whoever's driving.

Use this same pass periodically across the whole app (not just changed
screens) since pre-existing screens can have the same class of bug sitting
unnoticed — that's how the wipe-on-edit bug below was found, not through any
edit to that screen.

## Known sharp edges (found via TUI passes, now fixed — don't reintroduce)

- `db.update_entity()` replaces the entire `fields` JSON column. Any screen
  that edits a subset of fields (e.g. the generic flat-field form) must
  start from `dict(existing_entity["fields"])` and overlay just the keys it
  changed — never construct a fresh dict containing only the fields that
  screen knows about, or it silently wipes `sheet`/`active_effects`/`combat`
  data living alongside them.
- Use `Horizontal`, not `Container`, for any button row meant to lay out
  side-by-side. `Container`'s default layout is vertical; the shared CSS
  action-row rule (`height: auto; align: left middle;`) does not change
  that, it only aligns within whichever direction the widget already has.
- Every `ListView` needs its own `background`/`border` CSS (there's no
  global default) or it renders in Textual's bare default style, which
  clashes with the app's navy palette.
- `fields["level"]` (adventurer) and `fields["cr"]`/`fields["creature_type"]`
  (enemy) are flat denormalized copies of `fields["sheet"]["level"]` /
  `["cr"]` / `["creature_type"]`. Both the generic Edit form and the
  Character Sheet screen sync these on save (see `screens/entities.py`
  `EntityFormScreen.action_save` and `screens/sheet.py`
  `CharacterSheetScreen.action_save`) — if either gains a new duplicated
  flat/nested field pair, mirror that sync in both directions.
