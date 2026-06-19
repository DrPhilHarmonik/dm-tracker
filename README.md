# DM Tracker

A terminal campaign manager for Dungeon Masters, built with Textual and SQLite.

## Features

- Track NPCs, adventurers, locations, quests, factions, items, and sessions.
- Add typed fields and freeform notes for each entity.
- Create relationships between entities, including while creating a new entity (no need to save first).
- Search across every entity's name and notes from one global search screen (`/` on the dashboard).
- Export the campaign to Markdown files suitable for an Obsidian vault.
- Back up and restore the full campaign as JSON, from the dashboard (`b`) or the CLI.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python3 dm.py
```

By default, campaign data is stored at:

```text
~/.config/dm/campaign.db
```

You can point the app at a different database with `DM_DB_PATH`:

```bash
DM_DB_PATH=/path/to/campaign.db python3 dm.py
```

## Export

Use the dashboard export action or press `e` to export Markdown files. The default export location is:

```text
~/campaign_vault
```

A toggle on the export screen controls whether full character sheets and
active effects are included (as structured YAML frontmatter plus a
readable summary) or left out for a lighter, narrative-only vault.

## Markdown Vault Import

A vault exported by this app (not an arbitrary hand-authored Obsidian vault)
can be imported back in from the Backup & Restore screen (`b` on the
dashboard), or replace all current data. This round-trips entities, notes,
relationships, character sheets, and active effects losslessly when the
vault was exported with stats included.

## JSON Backup And Restore

Create a full-fidelity JSON backup:

```bash
python3 dm.py --backup-json backup.json
```

Restore into an empty database:

```bash
python3 dm.py --import-json backup.json
```

Replace the current database contents during restore:

```bash
python3 dm.py --import-json backup.json --replace
```

## Development

Install development dependencies:

```bash
pip install -r requirements.txt
```

Run tests:

```bash
python3 -m pytest
```
