#!/usr/bin/env python3
"""DM Tracker - CLI resource for Dungeon Masters."""
import argparse
import sys
import os

# Run from project dir so relative imports work
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from app import main
import db
import export as exp


def parse_args():
    parser = argparse.ArgumentParser(description="DM Tracker")
    parser.add_argument("--backup-json", help="Write a full-fidelity JSON backup to this path")
    parser.add_argument("--import-json", help="Import a full-fidelity JSON backup from this path")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing data when importing JSON",
    )
    return parser.parse_args()


def run_cli(args) -> int:
    if args.backup_json and args.import_json:
        print("Use either --backup-json or --import-json, not both.", file=sys.stderr)
        return 2

    if args.backup_json:
        db.init_db()
        count = exp.export_json_backup(args.backup_json)
        print(f"Backed up {count} entities to {args.backup_json}")
        return 0

    if args.import_json:
        db.init_db()
        result = exp.import_json_backup(args.import_json, replace=args.replace)
        print(
            f"Imported {result['entities']} entities and "
            f"{result['relationships']} relationships from {args.import_json}"
        )
        return 0

    main()
    return 0

if __name__ == "__main__":
    raise SystemExit(run_cli(parse_args()))
